# core/validation.py

from core.data_models import ValidationResult

class DataValidator:
    """Validation centralisée des données de l'application."""
    
    @staticmethod
    def validate_mois_data(nom: str, salaire: str) -> ValidationResult:
        errors = []
        validated_data = {}
        
        if not nom or not nom.strip():
            errors.append("Le nom du mois est requis")
        else:
            validated_data['nom'] = nom.strip()
        
        try:
            validated_salaire = float(salaire.replace(',', '.')) if salaire else 0.0
            if validated_salaire < 0:
                errors.append("Le salaire ne peut pas être négatif")
            validated_data['salaire'] = validated_salaire
        except (ValueError, AttributeError):
            errors.append("Le salaire doit être un nombre valide")
            validated_data['salaire'] = 0.0
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            validated_data=validated_data
        )
    
    @staticmethod
    def validate_expense_data(nom: str, montant: str, categorie: str) -> ValidationResult:
        errors = []
        validated_data = {}
        
        validated_data['nom'] = nom.strip() if nom else ""
        
        try:
            validated_montant = float(montant.replace(',', '.')) if montant else 0.0
            if validated_montant < 0:
                errors.append("Le montant ne peut pas être négatif")
            validated_data['montant'] = validated_montant
        except (ValueError, AttributeError):
            errors.append("Le montant doit être un nombre valide")
            validated_data['montant'] = 0.0
        
        validated_data['categorie'] = categorie if categorie else "Autres"
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            validated_data=validated_data
        )