# core/data_models.py

from dataclasses import dataclass, asdict
from typing import List, Optional, Any, Dict

# ===== EXCEPTIONS PERSONNALISÉES =====
class BudgetAppError(Exception): pass
class DatabaseError(BudgetAppError): pass
class ValidationError(BudgetAppError): pass
class ImportExportError(BudgetAppError): pass

# ===== CLASSES DE RÉSULTAT =====
@dataclass
class Result:
    is_success: bool
    message: str = ""
    error: str = ""
    data: Any = None
    
    @classmethod
    def success(cls, message: str = "", data: Any = None) -> 'Result':
        return cls(is_success=True, message=message, data=data)
    
    @classmethod
    def error(cls, error: str) -> 'Result':
        return cls(is_success=False, error=error)

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    validated_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.validated_data is None:
            self.validated_data = {}

# ===== ENTITÉS DE DONNÉES (DTOs) =====
@dataclass
class Depense:
    id: Optional[int] = None
    nom: str = ''
    montant: float = 0.0
    categorie: str = 'Autres'
    date_depense: str = ''
    est_credit: bool = False
    effectue: bool = False
    emprunte: bool = False
    est_fixe: bool = False

@dataclass
class Mois:
    nom: str
    salaire: float = 0.0
    date_creation: Optional[str] = None
    id: Optional[int] = None

@dataclass
class MoisDisplayData:
    nom: str
    salaire: float
    depenses: List[Depense]
    nombre_depenses: int
    total_depenses: float
    argent_restant: float
    total_effectue: float
    total_non_effectue: float
    total_emprunte: float

# ===== PATTERN OBSERVER =====
class Observable:
    def __init__(self):
        self._observers = []
    
    def add_observer(self, observer):
        if observer not in self._observers:
            self._observers.append(observer)
    
    def notify_observers(self, event_type: str, data: Any = None):
        for observer in self._observers:
            observer.on_model_changed(event_type, data)

class Observer:
    def on_model_changed(self, event_type: str, data: Any):
        pass