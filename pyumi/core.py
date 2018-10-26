import numpy as np
import pandas as pd

from .utils import log
import logging as lg
from . import settings, object_from_idf, object_from_idfs, simple_glazing


def convert_necb_to_umi_json(idfs, idfobjects=None):
    # if no list of idfobjects:
    if idfobjects is None:
        idfobjects = settings.useful_idf_objects

    for idf, idfobject in zip(idfs, idfobjects):
        print(object_from_idf(idf, idfobject))


def gas_type(row):
    """
    Return the UMI gas type number
    :param row: Dataframe
        row
    :return: int
        UMI gas type number
    """
    if 'air' in row['Name'].lower():
        return 0
    elif 'argon' in row['Name'].lower():
        return 1
    elif 'krypton' in row['Name'].lower():
        return 2
    elif 'xenon' in row['Name'].lower():
        return 3
    elif 'sf6' in row['Name'].lower():
        return 4


def materials_gas(idfs):
    materials_df = object_from_idfs(idfs, 'WINDOWMATERIAL:GAS')
    cols = settings.common_umi_objects['GasMaterials']

    # Add Type of gas column
    materials_df['Type'] = 'Gas'
    materials_df['GasType'] = materials_df.apply(lambda x: gas_type(x), axis=1)
    materials_df['Cost'] = 0
    materials_df['EmbodiedCarbon'] = 0
    materials_df['EmbodiedCarbonStdDev'] = 0
    materials_df['EmbodiedEnergy'] = 0
    materials_df['EmbodiedEnergyStdDev'] = 0
    materials_df['SubstitutionRatePattern'] = np.NaN  # ! Might have to change to an empty array
    materials_df['SubstitutionTimestep'] = 0
    materials_df['TransportCarbon'] = 0
    materials_df['TransportDistance'] = 0
    materials_df['TransportEnergy'] = 0
    materials_df['Life'] = 1  # TODO: What does Life mean? Always 1 in Boston Template
    materials_df['Comment'] = ''
    try:
        materials_df['DataSource'] = materials_df.pop('Archetype')
    except Exception as e:
        log('Error: {}'.format(e))
        materials_df['DataSource'] = 'First IDF file containing this common object'

    materials_df = materials_df.reset_index(drop=True).rename_axis('$id').reset_index()
    log('Returning {} WINDOWMATERIAL:GAS objects in a DataFrame'.format(len(materials_df)))
    return materials_df[cols].set_index('$id')  # Keep only relevant columns


def materials_glazing(idfs):
    materials_df = object_from_idfs(idfs, 'WINDOWMATERIAL:GLAZING')
    # materials_df = pd.concat([value['Materials'] for value in df.values()], keys=df.keys())
    # materials_df = materials_df.rename_axis(['Archetype', 'Index']).reset_index().rename_axis('$id')
    cols = settings.common_umi_objects['GlazingMaterials']

    column_rename = {'Optical_Data_Type': 'Optical',
                     'Window_Glass_Spectral_Data_Set_Name': 'OpticalData',
                     'Solar_Transmittance_at_Normal_Incidence': 'SolarTransmittance',
                     'Front_Side_Solar_Reflectance_at_Normal_Incidence': 'SolarReflectanceFront',
                     'Back_Side_Solar_Reflectance_at_Normal_Incidence': 'SolarReflectanceBack',
                     'Infrared_Transmittance_at_Normal_Incidence': 'IRTransmittance',
                     'Visible_Transmittance_at_Normal_Incidence': 'VisibleTransmittance',
                     'Front_Side_Visible_Reflectance_at_Normal_Incidence': 'VisibleReflectanceFront',
                     'Back_Side_Visible_Reflectance_at_Normal_Incidence': 'VisibleReflectanceBack',
                     'Front_Side_Infrared_Hemispherical_Emissivity': 'IREmissivityFront',
                     'Back_Side_Infrared_Hemispherical_Emissivity': 'IREmissivityBack',
                     'Dirt_Correction_Factor_for_Solar_and_Visible_Transmittance': 'DirtFactor'}

    # materials_df = materials_df.loc[materials_df.MaterialType == 10]
    materials_df.rename(columns=column_rename, inplace=True)
    materials_df['Comment'] = 'default'
    materials_df['Cost'] = 0
    try:
        materials_df['DataSource'] = materials_df.pop('Archetype')
    except:
        materials_df['DataSource'] = 'First IDF file containing this common object'
    materials_df['Density'] = 2500
    materials_df['EmbodiedCarbon'] = 0
    materials_df['EmbodiedCarbonStdDev'] = 0
    materials_df['EmbodiedEnergy'] = 0
    materials_df['EmbodiedEnergyStdDev'] = 0
    materials_df['Life'] = 1
    materials_df['SubstitutionRatePattern'] = np.NaN  # TODO: ! Might have to change to an empty array
    materials_df['SubstitutionTimestep'] = 0
    materials_df['TransportCarbon'] = 0
    materials_df['TransportDistance'] = 0
    materials_df['TransportEnergy'] = 0
    materials_df['Type'] = 'Uncoated'  # TODO Further investigation necessary

    materials_df = materials_df.reset_index(drop=True).rename_axis('$id').reset_index()

    # Now, we create glazing materials using the 'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM' objects and append them to the
    # list.
    # Try to get simple_glazing_systems
    sgs = get_simple_glazing_system(idfs)
    if not sgs.empty:
        log('Found {} WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM objects. Appending to WINDOWMATERIAL:GLAZING '
            'list...'.format(len(sgs)))
        materials_df = materials_df.set_index('$id').append(sgs, ignore_index=True, sort=True)
    materials_df = materials_df.reset_index(drop=True).rename_axis('$id').reset_index()
    # Return the Dataframe
    log('Returning {} WINDOWMATERIAL:GLAZING objects in a DataFrame'.format(len(materials_df)))
    return materials_df[cols].set_index('$id')


def get_simple_glazing_system(idfs):
    try:
        materials_df = object_from_idfs(idfs, 'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM')

        materials_df = materials_df.set_index('Name').apply(lambda row: simple_glazing(row[
                                                                                              'Solar_Heat_Gain_Coefficient'],
                                                                     row['UFactor'],
                                                                     row['Visible_Transmittance']), axis=1).apply(pd.Series)
        materials_df = materials_df.reset_index().rename_axis('Name')
        materials_df['Optical'] = 'SpectralAverage'
        materials_df['OpticalData'] = ''
        materials_df['DataSource'] = 'EnergyPlus Simple Glazing Calculation'
        materials_df['key'] = 'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM'
    except Exception as e:
        log('Error: {}'.format(e), lg.ERROR)
        return pd.DataFrame([])
    else:
        return materials_df

