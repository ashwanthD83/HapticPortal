#!/usr/bin/env python3
"""
Config Persistence for OAK-D Lite Hand Tracking

Safely reads and writes configuration files without corruption.
"""

import os
import re
import shutil
from typing import Dict, Any, Optional, Tuple


class ConfigPersistence:
    """Safely read and write configuration files."""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.backup_path = config_path + ".backup"
    
    def read_config(self) -> Dict[str, Any]:
        """Read current configuration values."""
        config = {}
        
        if not os.path.exists(self.config_path):
            return config
        
        try:
            with open(self.config_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse HAND_DEPTH_MIN and HAND_DEPTH_MAX
            for line in content.split('\n'):
                parsed = self.parse_config_line(line)
                if parsed:
                    var_name, value = parsed
                    config[var_name] = value
            
            return config
        
        except Exception as e:
            print(f"Error reading config: {e}")
            return config
    
    def write_config(self, depth_min: int, depth_max: int) -> bool:
        """Write depth range to config file, return success."""
        if not os.path.exists(self.config_path):
            print(f"Warning: Config file not found: {self.config_path}")
            return False
        
        try:
            # Create backup
            if not self.create_backup():
                return False
            
            # Read entire file
            with open(self.config_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Update lines
            updated_lines = []
            min_updated = False
            max_updated = False
            
            for line in lines:
                if 'HAND_DEPTH_MIN' in line and '=' in line and not line.strip().startswith('#'):
                    # Update HAND_DEPTH_MIN
                    updated_lines.append(self.format_config_line('HAND_DEPTH_MIN', depth_min))
                    min_updated = True
                elif 'HAND_DEPTH_MAX' in line and '=' in line and not line.strip().startswith('#'):
                    # Update HAND_DEPTH_MAX
                    updated_lines.append(self.format_config_line('HAND_DEPTH_MAX', depth_max))
                    max_updated = True
                else:
                    updated_lines.append(line)
            
            # Write back
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.writelines(updated_lines)
            
            if not min_updated or not max_updated:
                print(f"Warning: Could not find HAND_DEPTH_MIN or HAND_DEPTH_MAX in config")
                return False
            
            return True
        
        except Exception as e:
            print(f"Error writing config: {e}")
            # Restore backup
            self.restore_backup()
            return False
    
    def create_backup(self) -> bool:
        """Create backup of current config file."""
        try:
            if os.path.exists(self.config_path):
                shutil.copy2(self.config_path, self.backup_path)
                return True
            return False
        except Exception as e:
            print(f"Error creating backup: {e}")
            return False
    
    def restore_backup(self) -> bool:
        """Restore config from backup if write fails."""
        try:
            if os.path.exists(self.backup_path):
                shutil.copy2(self.backup_path, self.config_path)
                return True
            return False
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False
    
    def parse_config_line(self, line: str) -> Optional[Tuple[str, Any]]:
        """Parse a config line into (variable_name, value)."""
        # Skip comments and empty lines
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            return None
        
        # Match variable assignment
        match = re.match(r'(\w+)\s*=\s*(.+)', stripped)
        if match:
            var_name = match.group(1)
            value_str = match.group(2).strip()
            
            # Only parse depth-related variables
            if var_name in ['HAND_DEPTH_MIN', 'HAND_DEPTH_MAX']:
                try:
                    # Try to parse as integer
                    value = int(value_str)
                    return (var_name, value)
                except ValueError:
                    pass
        
        return None
    
    def format_config_line(self, var_name: str, value: Any) -> str:
        """Format a variable assignment line."""
        return f"{var_name} = {value}\n"
