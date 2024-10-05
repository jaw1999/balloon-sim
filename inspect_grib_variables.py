# inspect_grib2_pygrib.py

import pygrib

def inspect_grib2(filepath):
    try:
        grbs = pygrib.open(filepath)
        variables_info = {}
        
        for grb in grbs:
            name = grb.name
            short_name = grb.shortName
            type_of_level = grb.typeOfLevel
            step_type = grb.stepType
            level = grb.level
            param_id = grb.paramId
            
            key = (type_of_level, step_type)
            if key not in variables_info:
                variables_info[key] = []
            variables_info[key].append({
                'paramId': param_id,
                'name': name,
                'shortName': short_name,
                'level': level
            })
        
        grbs.close()
        
        # Print the collected information
        for key, variables in variables_info.items():
            type_of_level, step_type = key
            print(f"TypeOfLevel: {type_of_level}, StepType: {step_type}")
            for var in variables:
                print(f"  ParamId: {var['paramId']}, Name: {var['name']}, ShortName: {var['shortName']}, Level: {var['level']}")
            print()
        
    except Exception as e:
        print(f"Error inspecting GRIB2 file with pygrib: {e}")

if __name__ == "__main__":
    # Replace with your actual file path
    filepath = 'data/atmospheric_data/gfs.t12z.pgrb2.0p25.f024'
    inspect_grib2(filepath)
