from django import template

register = template.Library()

@register.filter(name='filter_by_status')
def filter_by_status(orders, status):
    """Filter orders by status"""
    if not orders:
        return []
    
    if status:
        return [order for order in orders if order.status == status]
    else:
        # Return all except cancelled/completed for "active" filter
        return [order for order in orders if order.status not in ['cancelled', 'completed']]

@register.filter(name='get_form_by_index')
def get_form_by_index(forms_dict, index):
    """Get form by index from dictionary or list."""
    if not forms_dict:
        return None
    
    try:
        index = int(index)
        
        # If forms_dict is a dictionary
        if isinstance(forms_dict, dict):
            keys = list(forms_dict.keys())
            if index < len(keys):
                return forms_dict[keys[index]]
        
        # If forms_dict is a list
        elif isinstance(forms_dict, list):
            if index < len(forms_dict):
                return forms_dict[index]
                
    except (ValueError, TypeError, IndexError):
        pass
    
    return None

# Also register the old name for compatibility
@register.filter(name='filter_status')
def filter_status(orders, status):
    """Alias for filter_by_status"""
    return filter_by_status(orders, status)

@register.filter(name='index')
def index(indexable, i):
    """Get item at index from list or split string"""
    try:
        return indexable[i]
    except (IndexError, TypeError, KeyError):
        return ''