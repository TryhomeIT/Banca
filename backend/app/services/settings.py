from sqlalchemy.orm import Session
from ..models.models import SystemSettings
from typing import Dict, Any, Optional

class SettingsService:
    @staticmethod
    def get_setting(db: Session, key: str, default: Any = None) -> Any:
        setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
        return setting.value if setting else default

    @staticmethod
    def set_setting(db: Session, key: str, value: str, category: str = "general", description: str = None):
        setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
            setting.category = category
        else:
            setting = SystemSettings(key=key, value=value, category=category, description=description)
            db.add(setting)
        db.commit()
        db.refresh(setting)
        return setting

    @staticmethod
    def get_all_settings(db: Session) -> Dict[str, Any]:
        settings = db.query(SystemSettings).all()
        return {s.key: s.value for s in settings}

    @staticmethod
    def get_settings_by_category(db: Session, category: str) -> Dict[str, Any]:
        settings = db.query(SystemSettings).filter(SystemSettings.category == category).all()
        return {s.key: s.value for s in settings}

settings_service = SettingsService()
