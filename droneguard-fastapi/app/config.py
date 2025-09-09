import yaml
from pathlib import Path
from typing import Union

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> dict:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as file:
            return yaml.safe_load(file)
    
    @property
    def app_title(self) -> str:
        return self._config['app']['title']
    
    @property
    def app_description(self) -> str:
        return self._config['app']['description']
    
    @property
    def app_version(self) -> str:
        return self._config['app']['version']
    
    @property
    def host(self) -> str:
        return self._config['app']['host']
    
    @property
    def port(self) -> int:
        return self._config['app']['port']
    
    @property
    def debug(self) -> bool:
        return self._config['app']['debug']
    
    @property
    def video_source(self) -> Union[int, str]:
        source = self._config['video']['source']
        return int(source) if str(source).isdigit() else source
    
    @property
    def video_width(self) -> int:
        return self._config['video']['width']
    
    @property
    def video_height(self) -> int:
        return self._config['video']['height']
    
    @property
    def video_fps(self) -> int:
        return self._config['video']['fps']
    
    @property
    def model_path(self) -> str:
        return self._config['model']['path']
    
    @property
    def confidence_threshold(self) -> float:
        return self._config['model']['confidence_threshold']
    
    @property
    def iou_threshold(self) -> float:
        return self._config['model']['iou_threshold']
    
    @property
    def input_size(self) -> int:
        return self._config['model']['input_size']
    
    @property
    def streaming_quality(self) -> int:
        return self._config['streaming']['quality']
    
    @property
    def buffer_size(self) -> int:
        return self._config['streaming']['buffer_size']

# Global config instance
config = Config()