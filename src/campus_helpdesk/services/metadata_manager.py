import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class MetadataManager:
    """Manages metadata verification, semantic validation, and frontmatter formatting."""

    CONTROLLED_DOC_TYPES = {
        "program-detail", "curriculum", "regulation", "report", "minutes", "accreditation", 
        "brochure", "timetable", "notice", "news", "committee", "facility", "contact", "faq", 
        "profile", "landing-page", "policy", "financial", "research-center", "placement-data", 
        "event", "gallery", "publication"
    }

    CONTROLLED_ENTITY_TYPES = {"program", "department", "school", "campus", "facility", "committee", "governance", "general", "people"}

    OFFICIAL_DEPARTMENTS = {
        "Civil Engineering", "Computer Science & Engineering", "Electronics & Communication Engineering",
        "Electrical & Electronics Engineering", "Mechanical Engineering", "Automation & Robotics", 
        "Biotechnology", "Chemical Engineering", "Biomedical Engineering", "Architecture",
        "School of Management Studies & Research", "School of Computer Applications",
        "School of Commerce", "School of Law", "School of Advanced Sciences",
        "School of Fashion & Design", ""
    }

    @classmethod
    def validate(cls, metadata: Dict[str, Any]) -> List[str]:
        """Validate metadata fields against controlled vocabularies.
        
        Returns a list of validation warnings/errors.
        """
        warnings = []
        
        # Check doc_type
        doc_type = metadata.get("document_type", "")
        if doc_type and doc_type not in cls.CONTROLLED_DOC_TYPES:
            warnings.append(f"document_type '{doc_type}' is not in controlled vocabulary.")
            
        # Check entity_type
        entity_type = metadata.get("entity_type", "")
        if entity_type and entity_type not in cls.CONTROLLED_ENTITY_TYPES:
            warnings.append(f"entity_type '{entity_type}' is not in controlled vocabulary.")
            
        # Check department
        dept = metadata.get("department", "")
        if dept and dept not in cls.OFFICIAL_DEPARTMENTS:
            warnings.append(f"department '{dept}' is not an official university department name.")
            
        # Check campus
        campus = metadata.get("campus_scope", "")
        if campus and campus not in {"Hubballi", "Belagavi", "Bengaluru", "All"}:
            warnings.append(f"campus_scope '{campus}' is invalid; must be Hubballi, Belagavi, Bengaluru, or All.")
            
        return warnings

    @classmethod
    def format_frontmatter(cls, metadata: Dict[str, Any]) -> str:
        """Format metadata dict as YAML frontmatter block."""
        import yaml
        yaml_content = yaml.safe_dump(metadata, default_flow_style=False, sort_keys=False)
        return f"---\n{yaml_content}---"
