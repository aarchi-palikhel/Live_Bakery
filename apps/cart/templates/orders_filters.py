from django import template

register = template.Library()

@register.filter
def get_form_by_index(forms_dict, index):
    """Get form by index from dictionary"""
    if forms_dict and index < len(forms_dict):
        # If forms_dict is a dict, get values
        if isinstance(forms_dict, dict):
            keys = list(forms_dict.keys())
            if index < len(keys):
                return forms_dict[keys[index]]
        # If forms_dict is a list
        elif isinstance(forms_dict, list) and index < len(forms_dict):
            return forms_dict[index]
    return None