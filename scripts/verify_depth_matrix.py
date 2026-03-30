#!/usr/bin/env python3
"""
Depth Matrix Verification Utility

Two modes are supported:
1) Live OAK-D capture (default).
2) Static depth image verification via --depth-image (useful for NYU v2 samples).

Verification checks the same 5x5 pipeline used by the app:
1) clip depth to max range
2) normalize to uint8 [0, 255]
3) downscale to 5x5 using INTER_AREA
"""

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.depth_processor import clip_depth, normalize_depth, downscale_depth, process_depth_frame


class DepthFrameAdapter:
    """Adapter to reuse process_depth_frame() with static arrays."""

    def __init__(self, depth_array):
        self._depth_array = depth_array

    def getFrame(self):
        return self._depth_array


def create_depth_pipeline(dai):
    """Create a minimal stereo depth pipeline."""
    pipeline = dai.Pipeline()

    mono_left = pipeline.create(dai.node.MonoCamera)
    mono_right = pipeline.create(dai.node.MonoCamera)
    stereo = pipeline.create(dai.node.StereoDepth)
    xout_depth = pipeline.create(dai.node.XLinkOut)

    mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    mono_left.setBoardSocket(dai.CameraBoardSocket.CAM_B)
    mono_right.setBoardSocket(dai.CameraBoardSocket.CAM_C)

    stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_ACCURACY)
    stereo.setLeftRightCheck(True)
    stereo.setExtendedDisparity(False)
    stereo.setSubpixel(False)

    xout_depth.setStreamName("depth")

    mono_left.out.link(stereo.left)
    mono_right.out.link(stereo.right)
    stereo.depth.link(xout_depth.input)

    return pipeline


def render_matrix_panel(matrix_5x5, title, panel_size=320):
    """Render a readable matrix panel with numeric values."""
    panel = np.zeros((panel_size, panel_size, 3), dtype=np.uint8)
    panel[:] = (25, 25, 25)
    cv2.putText(panel, title, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    grid_top = 40
    grid_size = panel_size - grid_top - 10
    cell = grid_size // 5

    matrix_u8 = matrix_5x5.astype(np.uint8)
    upscaled = cv2.resize(matrix_u8, (cell * 5, cell * 5), interpolation=cv2.INTER_NEAREST)
    colorized = cv2.applyColorMap(upscaled, cv2.COLORMAP_TURBO)
    panel[grid_top:grid_top + cell * 5, 10:10 + cell * 5] = colorized

    for row in range(5):
        for col in range(5):
            x0 = 10 + col * cell
            y0 = grid_top + row * cell
            x1 = x0 + cell
            y1 = y0 + cell
            cv2.rectangle(panel, (x0, y0), (x1, y1), (220, 220, 220), 1)
            value = int(matrix_5x5[row, col])
            cv2.putText(
                panel,
                str(value),
                (x0 + 8, y0 + int(cell * 0.62)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.50,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

    return panel


def reduce_to_5x5_block_mean(array_2d):
    """Independent reference reducer using explicit 5x5 block means."""
    arr = np.asarray(array_2d, dtype=np.float32)
    h, w = arr.shape
    row_edges = np.linspace(0, h, 6, dtype=int)
    col_edges = np.linspace(0, w, 6, dtype=int)

    out = np.zeros((5, 5), dtype=np.float32)
    for i in range(5):
        for j in range(5):
            block = arr[row_edges[i]:row_edges[i + 1], col_edges[j]:col_edges[j + 1]]
            if block.size:
                out[i, j] = float(block.mean())

    return out


def _prepare_rgb_preview(rgb_raw):
    """Convert h5 rgb tensor to displayable BGR uint8 image."""
    rgb = np.asarray(rgb_raw)
    rgb = np.squeeze(rgb)

    if rgb.ndim == 2:
        rgb = np.stack([rgb, rgb, rgb], axis=-1)
    elif rgb.ndim == 3 and rgb.shape[0] in (1, 3, 4) and rgb.shape[0] < rgb.shape[-1]:
        rgb = np.transpose(rgb, (1, 2, 0))

    if rgb.ndim != 3:
        return None

    if rgb.shape[2] == 1:
        rgb = np.repeat(rgb, repeats=3, axis=2)
    elif rgb.shape[2] > 3:
        rgb = rgb[:, :, :3]

    rgb = rgb.astype(np.float32)
    finite = rgb[np.isfinite(rgb)]
    if finite.size:
        max_val = float(finite.max())
        min_val = float(finite.min())
    else:
        max_val, min_val = 0.0, 0.0

    if max_val <= 1.0 and min_val >= 0.0:
        rgb *= 255.0

    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    # h5 rgb data is typically RGB; convert to BGR for OpenCV display.
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def build_dashboard(
    depth_norm_u8,
    matrix_processed,
    matrix_manual,
    matrix_reference,
    diff_process_vs_reference,
    sample_idx,
    frame_idx,
    rgb_preview=None,
):
    """Build a combined visualization image."""
    depth_color = cv2.applyColorMap(depth_norm_u8, cv2.COLORMAP_TURBO)
    depth_view = cv2.resize(depth_color, (960, 400), interpolation=cv2.INTER_LINEAR)
    cv2.putText(
        depth_view,
        f"Sample {sample_idx} | Source frame {frame_idx}",
        (20, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2,
    )
    cv2.putText(
        depth_view,
        "Depth (normalized color map)",
        (20, 66),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        1,
    )

    if rgb_preview is not None and rgb_preview.size:
        rgb_inset = cv2.resize(rgb_preview, (240, 180), interpolation=cv2.INTER_LINEAR)
        depth_view[10:190, 710:950] = rgb_inset
        cv2.rectangle(depth_view, (710, 10), (950, 190), (255, 255, 255), 1)
        cv2.putText(depth_view, "RGB Input", (716, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    processed_panel = render_matrix_panel(matrix_processed, "process_depth_frame()", panel_size=240)
    manual_panel = render_matrix_panel(matrix_manual, "manual cv2 area", panel_size=240)
    reference_panel = render_matrix_panel(matrix_reference, "reference block mean", panel_size=240)
    diff_vis = np.clip(diff_process_vs_reference.astype(np.int16) * 32, 0, 255).astype(np.uint8)
    diff_panel = render_matrix_panel(diff_vis, "diff(process, ref) x32", panel_size=240)

    bottom = np.hstack([processed_panel, manual_panel, reference_panel, diff_panel])
    dashboard = np.vstack([depth_view, bottom])
    return dashboard


def parse_args():
    parser = argparse.ArgumentParser(
        description="Verify 5x5 depth matrix calculations using live OAK-D frames or one static depth image."
    )
    parser.add_argument(
        "--depth-image",
        type=str,
        default="",
        help="Path to a static depth input (.png/.jpg/.tiff/.h5). If provided, live camera is not used.",
    )
    parser.add_argument(
        "--h5-depth-key",
        type=str,
        default="depth",
        help="Dataset key to read from .h5 files (default: depth).",
    )
    parser.add_argument(
        "--h5-rgb-key",
        type=str,
        default="rgb",
        help="Optional RGB key to read from .h5 files for visualization (default: rgb).",
    )
    parser.add_argument(
        "--depth-scale",
        type=float,
        default=1.0,
        help="Scale factor applied to loaded depth image values before clipping.",
    )
    parser.add_argument("--samples", type=int, default=5, help="How many sample frames to capture.")
    parser.add_argument("--warmup", type=int, default=20, help="Frames to discard before sampling.")
    parser.add_argument("--stride", type=int, default=15, help="Capture one sample every N frames after warmup.")
    parser.add_argument("--max-mm", type=int, default=5000, help="Depth max used for clipping/normalization.")
    parser.add_argument("--save-dir", type=str, default="verification_output", help="Output directory for PNG/JSON.")
    parser.add_argument("--pause-ms", type=int, default=900, help="Display pause per sample in ms.")
    parser.add_argument("--no-display", action="store_true", help="Disable OpenCV display windows.")
    return parser.parse_args()


def _convert_depth_to_uint16_mm(raw, max_mm, depth_scale):
    """Convert raw depth array to uint16 millimeter-like values."""
    depth = raw.astype(np.float32)

    if raw.dtype == np.uint8:
        # If only 8-bit values are available, map to [0, max_mm].
        depth = (depth / 255.0) * float(max_mm)
    elif np.issubdtype(raw.dtype, np.floating):
        finite = depth[np.isfinite(depth)]
        max_val = float(finite.max()) if finite.size else 0.0
        # Heuristic: values in [0, ~20] are often meters.
        if max_val > 0 and max_val <= 20.0:
            depth *= 1000.0

    depth *= float(depth_scale)
    depth = np.nan_to_num(depth, nan=0.0, posinf=0.0, neginf=0.0)
    depth = np.clip(depth, 0, 65535).astype(np.uint16)
    return depth


def _ensure_2d_depth(raw):
    """Ensure loaded depth array is 2D."""
    raw = np.asarray(raw)
    raw = np.squeeze(raw)
    if raw.ndim == 2:
        return raw
    if raw.ndim == 3:
        # Handle channel-first or channel-last tensors by selecting one channel.
        channel_axis = int(np.argmin(raw.shape))
        raw = np.take(raw, indices=0, axis=channel_axis)
        raw = np.squeeze(raw)
        if raw.ndim == 2:
            return raw
    raise ValueError(f"Depth input must be 2D after squeeze; got shape {tuple(np.asarray(raw).shape)}")


def load_static_depth_input(depth_path, max_mm, depth_scale, h5_depth_key, h5_rgb_key):
    """Load static depth from image or h5 and convert to millimeter-like uint16."""
    suffix = depth_path.suffix.lower()

    if suffix in [".h5", ".hdf5"]:
        try:
            import h5py
        except Exception as exc:
            raise RuntimeError(
                f"h5py is required for .h5 inputs. Install it in your venv (pip install h5py). Details: {exc}"
            ) from exc

        with h5py.File(str(depth_path), "r") as handle:
            if h5_depth_key not in handle:
                available = list(handle.keys())
                raise KeyError(f"H5 key '{h5_depth_key}' not found. Available keys: {available}")
            raw = handle[h5_depth_key][()]
            rgb_preview = None
            if h5_rgb_key in handle:
                try:
                    rgb_preview = _prepare_rgb_preview(handle[h5_rgb_key][()])
                except Exception:
                    rgb_preview = None

        raw = _ensure_2d_depth(raw)
        raw_dtype = str(raw.dtype)
        depth = _convert_depth_to_uint16_mm(raw, max_mm, depth_scale)
        return depth, raw_dtype, {"kind": "h5", "key": h5_depth_key, "rgb_key": h5_rgb_key}, rgb_preview

    raw = cv2.imread(str(depth_path), cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise FileNotFoundError(f"Could not read depth image: {depth_path}")

    if raw.ndim == 3:
        raw = cv2.cvtColor(raw, cv2.COLOR_BGR2GRAY)

    raw = _ensure_2d_depth(raw)
    raw_dtype = str(raw.dtype)
    depth = _convert_depth_to_uint16_mm(raw, max_mm, depth_scale)
    return depth, raw_dtype, {"kind": "image"}, None


def save_sample(depth_data, max_mm, output_dir, sample_idx, frame_idx, source, rgb_preview=None):
    """Compute verification artifacts for one depth sample and save results."""
    depth_clipped = clip_depth(depth_data, max_mm)
    depth_norm = normalize_depth(depth_clipped, max_mm)
    matrix_manual = downscale_depth(depth_norm, (5, 5))

    adapter = DepthFrameAdapter(depth_data)
    matrix_processed = process_depth_frame(adapter, max_mm=max_mm, target_size=(5, 5))
    matrix_reference = np.rint(reduce_to_5x5_block_mean(depth_norm)).astype(np.uint8)

    diff_process_vs_reference = np.abs(
        matrix_processed.astype(np.int16) - matrix_reference.astype(np.int16)
    ).astype(np.uint8)
    diff_process_vs_manual = np.abs(
        matrix_processed.astype(np.int16) - matrix_manual.astype(np.int16)
    ).astype(np.uint8)
    max_abs_diff = int(diff_process_vs_reference.max())
    mean_abs_diff = float(diff_process_vs_reference.mean())

    nonzero_depth = depth_data[depth_data > 0]
    min_mm = int(nonzero_depth.min()) if nonzero_depth.size else 0
    max_nonzero_mm = int(nonzero_depth.max()) if nonzero_depth.size else 0
    mean_mm = float(nonzero_depth.mean()) if nonzero_depth.size else 0.0

    depth_mm_5x5 = cv2.resize(depth_clipped.astype(np.float32), (5, 5), interpolation=cv2.INTER_AREA)

    dashboard = build_dashboard(
        depth_norm,
        matrix_processed,
        matrix_manual,
        matrix_reference,
        diff_process_vs_reference,
        sample_idx,
        frame_idx,
        rgb_preview=rgb_preview,
    )

    png_path = output_dir / f"sample_{sample_idx:02d}.png"
    json_path = output_dir / f"sample_{sample_idx:02d}.json"
    cv2.imwrite(str(png_path), dashboard)

    record = {
        "sample_index": sample_idx,
        "source_frame_index": frame_idx,
        "source": source,
        "raw_depth_stats_mm": {
            "min_nonzero": min_mm,
            "max_nonzero": max_nonzero_mm,
            "mean_nonzero": round(mean_mm, 3),
        },
        "matrix_5x5_mm_inter_area": np.round(depth_mm_5x5, 2).tolist(),
        "matrix_from_process_depth_frame": matrix_processed.tolist(),
        "matrix_from_manual_cv2_area": matrix_manual.tolist(),
        "matrix_from_reference_block_mean": matrix_reference.tolist(),
        "abs_diff_process_vs_manual": diff_process_vs_manual.tolist(),
        "abs_diff_process_vs_reference": diff_process_vs_reference.tolist(),
        "max_abs_difference": max_abs_diff,
        "mean_abs_difference": round(mean_abs_diff, 4),
        "image_path": str(png_path),
    }

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)

    return record, dashboard


def write_summary(sample_records, requested_samples, output_dir):
    summary = {
        "samples_captured": len(sample_records),
        "samples_requested": requested_samples,
        "max_abs_difference_overall": int(max(r["max_abs_difference"] for r in sample_records)),
        "mean_abs_difference_overall": float(np.mean([r["mean_abs_difference"] for r in sample_records])),
        "all_samples_exact_match": all(r["max_abs_difference"] == 0 for r in sample_records),
    }
    summary_path = output_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump({"summary": summary, "samples": sample_records}, handle, indent=2)
    print("-" * 72)
    print(f"Summary: {summary}")
    print(f"Saved: {summary_path}")
    print("-" * 72)


def run_static_mode(args, output_dir):
    depth_path = Path(args.depth_image)
    if not depth_path.is_absolute():
        depth_path = (ROOT / depth_path).resolve()

    depth_data, raw_dtype, meta, rgb_preview = load_static_depth_input(
        depth_path,
        args.max_mm,
        args.depth_scale,
        args.h5_depth_key,
        args.h5_rgb_key,
    )
    print(f"Mode: static input")
    print(f"Depth path: {depth_path}")
    print(f"Raw dtype: {raw_dtype} | Converted dtype: {depth_data.dtype} | Shape: {depth_data.shape}")

    record, dashboard = save_sample(
        depth_data=depth_data,
        max_mm=args.max_mm,
        output_dir=output_dir,
        sample_idx=1,
        frame_idx=1,
        source={"mode": "static_input", "path": str(depth_path), "raw_dtype": raw_dtype, **meta},
        rgb_preview=rgb_preview,
    )
    print(
        f"[sample 1/1] frame=1 max_diff={record['max_abs_difference']} "
        f"mean_diff={record['mean_abs_difference']:.4f}"
    )

    if not args.no_display:
        cv2.imshow("Depth Matrix Verifier", dashboard)
        cv2.waitKey(max(1, args.pause_ms))
        cv2.destroyAllWindows()

    write_summary([record], 1, output_dir)
    return 0


def run_live_mode(args, output_dir):
    try:
        import depthai as dai
    except Exception as exc:
        print(f"Failed to import depthai for live mode: {exc}")
        return 1

    print(f"Mode: live OAK-D")
    print(f"Samples: {args.samples} | Warmup: {args.warmup} | Stride: {args.stride}")

    pipeline = create_depth_pipeline(dai)
    sample_records = []

    with dai.Device(pipeline) as device:
        depth_queue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)

        frame_idx = 0
        sample_idx = 0
        while sample_idx < args.samples:
            depth_frame = depth_queue.get()
            if depth_frame is None:
                continue

            frame_idx += 1
            if frame_idx <= args.warmup:
                continue
            if (frame_idx - args.warmup) % args.stride != 0:
                continue

            sample_idx += 1
            depth_data = depth_frame.getFrame()
            record, dashboard = save_sample(
                depth_data=depth_data,
                max_mm=args.max_mm,
                output_dir=output_dir,
                sample_idx=sample_idx,
                frame_idx=frame_idx,
                source={"mode": "live_oak_d"},
                rgb_preview=None,
            )
            sample_records.append(record)

            print(
                f"[sample {sample_idx}/{args.samples}] frame={frame_idx} "
                f"max_diff={record['max_abs_difference']} "
                f"mean_diff={record['mean_abs_difference']:.4f}"
            )

            if not args.no_display:
                cv2.imshow("Depth Matrix Verifier", dashboard)
                key = cv2.waitKey(max(1, args.pause_ms)) & 0xFF
                if key == ord("q"):
                    print("Early stop requested by user.")
                    break

    if not args.no_display:
        cv2.destroyAllWindows()

    if not sample_records:
        print("No samples captured. Increase runtime or lower warmup/stride.")
        return 1

    write_summary(sample_records, args.samples, output_dir)
    return 0


def main():
    args = parse_args()
    output_dir = ROOT / args.save_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("Depth Matrix Verification")
    print("=" * 72)
    print(f"Output: {output_dir}")

    if args.depth_image:
        return run_static_mode(args, output_dir)
    return run_live_mode(args, output_dir)


if __name__ == "__main__":
    sys.exit(main())
