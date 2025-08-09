"""
Template Initialization Service
Service to populate the database with default activity templates.
"""

import logging
from google.cloud import firestore
from app.data.default_templates import get_default_activity_templates

logger = logging.getLogger(__name__)

class TemplateInitializationService:
    """Service for initializing default activity templates."""
    
    def __init__(self):
        """Initialize the template initialization service."""
        self.db = firestore.Client()
    
    def initialize_default_templates(self) -> bool:
        """
        Initialize the database with default activity templates.
        Only adds templates if they don't already exist.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if templates already exist
            existing_templates = self.db.collection('activity_templates').limit(1).stream()
            if len(list(existing_templates)) > 0:
                logger.info("Activity templates already exist, skipping initialization")
                return True
            
            # Get default templates
            default_templates = get_default_activity_templates()
            
            # Add templates to Firestore in batch
            batch = self.db.batch()
            
            for template in default_templates:
                doc_ref = self.db.collection('activity_templates').document(template.id)
                batch.set(doc_ref, template.to_dict())
            
            # Commit batch
            batch.commit()
            
            logger.info(f"Successfully initialized {len(default_templates)} default activity templates")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing default templates: {str(e)}")
            return False
    
    def reset_templates(self) -> bool:
        """
        Reset all activity templates and reinitialize with defaults.
        Use with caution - this will delete all existing templates.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete all existing templates
            templates_ref = self.db.collection('activity_templates')
            docs = templates_ref.stream()
            
            # Delete in batches of 500 (Firestore limit)
            batch = self.db.batch()
            count = 0
            
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
                
                if count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()
            
            # Commit remaining deletes
            if count % 500 != 0:
                batch.commit()
            
            logger.info(f"Deleted {count} existing templates")
            
            # Initialize default templates
            return self.initialize_default_templates()
            
        except Exception as e:
            logger.error(f"Error resetting templates: {str(e)}")
            return False
    
    def add_custom_template_collection(self, template_collection_name: str, templates: list) -> bool:
        """
        Add a custom collection of templates.
        
        Args:
            template_collection_name: Name for the collection
            templates: List of ActivityTemplate objects
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            batch = self.db.batch()
            
            for template in templates:
                doc_ref = self.db.collection('activity_templates').document(template.id)
                batch.set(doc_ref, template.to_dict())
            
            batch.commit()
            
            logger.info(f"Successfully added {len(templates)} templates from collection '{template_collection_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error adding template collection '{template_collection_name}': {str(e)}")
            return False
    
    def get_template_statistics(self) -> dict:
        """
        Get statistics about templates in the database.
        
        Returns:
            dict: Statistics about templates
        """
        try:
            templates_ref = self.db.collection('activity_templates')
            docs = templates_ref.stream()
            
            stats = {
                'total_count': 0,
                'by_subject': {},
                'by_type': {},
                'by_difficulty': {},
                'by_grade': {},
                'public_count': 0,
                'average_rating': 0,
                'total_usage': 0
            }
            
            total_rating = 0
            rating_count = 0
            
            for doc in docs:
                template_data = doc.to_dict()
                stats['total_count'] += 1
                
                # Count by subject
                subject = template_data.get('subject', 'Unknown')
                stats['by_subject'][subject] = stats['by_subject'].get(subject, 0) + 1
                
                # Count by type
                activity_type = template_data.get('type', 'Unknown')
                stats['by_type'][activity_type] = stats['by_type'].get(activity_type, 0) + 1
                
                # Count by difficulty
                difficulty = template_data.get('difficulty_level', 'Unknown')
                stats['by_difficulty'][difficulty] = stats['by_difficulty'].get(difficulty, 0) + 1
                
                # Count by grade
                grade = template_data.get('grade', 'Unknown')
                stats['by_grade'][grade] = stats['by_grade'].get(grade, 0) + 1
                
                # Count public templates
                if template_data.get('is_public', False):
                    stats['public_count'] += 1
                
                # Track ratings
                rating = template_data.get('rating', 0)
                if rating > 0:
                    total_rating += rating
                    rating_count += 1
                
                # Track usage
                stats['total_usage'] += template_data.get('usage_count', 0)
            
            # Calculate average rating
            if rating_count > 0:
                stats['average_rating'] = round(total_rating / rating_count, 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting template statistics: {str(e)}")
            return {}
    
    def health_check(self) -> dict:
        """
        Perform a health check on the template system.
        
        Returns:
            dict: Health check results
        """
        try:
            # Check database connection
            templates_ref = self.db.collection('activity_templates')
            test_query = templates_ref.limit(1).stream()
            list(test_query)  # Execute query
            
            # Get basic stats
            stats = self.get_template_statistics()
            
            return {
                'status': 'healthy',
                'database_connection': True,
                'template_count': stats.get('total_count', 0),
                'public_templates': stats.get('public_count', 0),
                'subjects_available': len(stats.get('by_subject', {})),
                'activity_types': len(stats.get('by_type', {}))
            }
            
        except Exception as e:
            logger.error(f"Template system health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'database_connection': False
            }
