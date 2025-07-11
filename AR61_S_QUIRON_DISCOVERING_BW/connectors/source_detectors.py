def determine_infosource_type(self, datasource_name):
    """NEW METHOD: Determine if DataSource is an InfoSource or external source"""

    # Common patterns to identify InfoSources vs external DataSources
    name_upper = datasource_name.upper()

    if name_upper.startswith('8'):
        return 'Generic InfoSource'
    elif name_upper.startswith('6'):
        return 'Application Component InfoSource'
    elif name_upper.startswith('0') and len(name_upper) >= 9:
        return 'SAP Standard InfoSource'
    elif 'ISOURCE' in name_upper:
        return 'Custom InfoSource'
    elif '_' in name_upper and len(name_upper.split('_')[0]) == 3:
        return 'External DataSource'
    else:
        return 'DataSource'


def get_source_system_info(self, datasource_name):
    """Enhanced method to extract source system information"""

    # Enhanced SAP BW DataSource naming patterns
    if '_' in datasource_name:
        parts = datasource_name.split('_')
        if len(parts) >= 2:
            potential_system = parts[0]
            if len(potential_system) == 3:  # Typical 3-character system ID
                return potential_system.upper()
            elif potential_system.startswith('0') and len(potential_system) >= 4:
                return f"SAP_{potential_system[:4]}"

    # Extract from common patterns
    name_upper = datasource_name.upper()
    if name_upper.startswith('0'):
        if len(name_upper) >= 9:
            return f"SAP_STANDARD_{name_upper[:4]}"
        else:
            return "SAP_STANDARD"
    elif name_upper.startswith('Z') or name_upper.startswith('Y'):
        return "CUSTOM_DEVELOPMENT"
    elif name_upper.startswith('8'):
        return "GENERIC_INFOSOURCE"
    elif name_upper.startswith('6'):
        return "APPLICATION_COMPONENT"
    elif 'SALES' in name_upper:
        return "SALES_SYSTEM"
    elif 'FI' in name_upper or 'FINANCE' in name_upper:
        return "FINANCE_SYSTEM"
    elif 'HR' in name_upper or 'HUMAN' in name_upper:
        return "HR_SYSTEM"
    elif 'MM' in name_upper or 'MATERIAL' in name_upper:
        return "MATERIALS_SYSTEM"
    else:
        return "EXTERNAL_SYSTEM"
