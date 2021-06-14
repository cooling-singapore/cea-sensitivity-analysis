"""
This tool run multiple iterations of CEA for studies of sensitivity analysis
"""
from __future__ import division
from __future__ import print_function
# from hyperopt.pyll import scope
import cea.config
import cea.inputlocator
from cea.utilities.dbf import dbf_to_dataframe, dataframe_to_dbf
from cea.datamanagement import archetypes_mapper
from cea.demand import demand_main, schedule_maker
from cea.demand.schedule_maker import schedule_maker
from cea_calibration.validation import *
from cea_calibration.global_variables import *
from cea.utilities.schedule_reader import read_cea_schedule, save_cea_schedule
from collections import OrderedDict
# from hyperopt import fmin, tpe, hp, Trials
import pandas as pd
import numpy as np
# import glob2
import os
import random

__author__ = "Luis Santos"
__copyright__ = "Copyright 2020, Architecture and Building Systems - ETH Zurich"
__credits__ = ["Cooling Singapore - Luis Santos"]
__license__ = "MIT"
__version__ = "1.0"
__maintainer__ = "Luis Santos"
__email__ = "cea@arch.ethz.ch"
__status__ = "Production"


class SensitivityAnalysisPlugin(cea.plugin.CeaPlugin):
    """
    Define the plugin class - unless you want to customize the behavior, you only really need to declare the class. The
    rest of the information will be picked up from ``default.config``, ``schemas.yml`` and ``scripts.yml`` by default.
    """
    pass

def sensitivty_params(config, locator):

    void_deck = random.randint(0,2)
    Es = random.gauss(0.8,1)
    Hs_ag = random.gauss(0.6,1)
    Ns = random.gauss(0.8,1)
    wwr = random.gauss(0.6,1)
    constr_type = "CONSTRUCTION_AS" + str(random.randint(1,3))
    leak_type = "TIGHTNESS_AS" + str(random.randint(1,6))
    roof_type = "ROOF_AS" + str(random.randint(1,7))
    shading_type = "SHADING_AS" + str(random.randint(0,2))
    wall_type = "WALL_AS" + str(random.randint(1,8))
    part_type = "WALL_AS" + str(random.randint(1,6))
    wind_type = "WINDOW_AS" + str(random.randint(1,10))
    Occ_m2pax = random.gauss(15,1)
    Qs_wp = random.gauss(70,1)
    X_ghp = random.gauss(70,1)
    Ea_Wm2 = random.gauss(11,1)
    El_Wm2 = random.gauss(10,1)
    Vww_lpdpax = random.gauss(40,1)
    Tcs_set_C = random.gauss(24,1)
    Ve_lsp = random.gauss(10, 1)
    cooling_type = "HVAC_COOLING_AS" + str(random.randint(1,5)) #account also for the supply system
    hot_water_type = "HVAC_HOTWATER_AS" + str(random.randint(0,4))
    controller_type = "HVAC_CONTROLLER_AS" + str(random.randint(0,4))
    ventilation_type = "HVAC_VENTILATION_AS" + str(random.randint(0,3))

    ## overwrite inputs

    # Changes and saves variables related to the architecture
    df_arch = dbf_to_dataframe(locator.get_building_architecture())
    df_arch.Es = Es
    df_arch.Ns = Ns
    df_arch.Hs_ag = Hs_ag
    df_arch.void_deck = void_deck
    dataframe_to_dbf(df_arch, locator.get_building_architecture())

    # Changes and saves variables related to intetnal loads
    df_intload = dbf_to_dataframe(locator.get_building_internal())
    df_intload.Occ_m2pax = Occ_m2pax
    df_intload.Vww_lpdpax = Vww_lpdpax
    df_intload.Ea_Wm2 = Ea_Wm2
    df_intload.El_Wm2 = El_Wm2
    dataframe_to_dbf(df_intload, locator.get_building_internal())

    # Changes and saves variables related to comfort
    df_comfort = dbf_to_dataframe(locator.get_building_comfort())
    df_comfort.Tcs_set_C = Tcs_set_C
    dataframe_to_dbf(df_comfort, locator.get_building_comfort())

    # Changes and saves variables related to zone
    df_zone = dbf_to_dataframe(locator.get_zone_geometry().split('.')[0] + '.dbf')
    df_zone.height_bg = height_bg
    df_zone.floors_bg = floors_bg
    dataframe_to_dbf(df_zone, locator.get_zone_geometry().split('.')[0] + '.dbf')

    ## run building schedules and energy demand
    config.schedule_maker.buildings = measured_building_names
    schedule_maker.schedule_maker_main(locator, config)
    config.demand.buildings = measured_building_names
    demand_main.demand_calculation(locator, config)

    ## get total energy demand
    energy_demand = pd.read_csv(locator.get_total_demand(),
                                       usecols=['Name', 'GRID_MWhyr'])

    return energy_demand


def sensitivity_setup(config, locator):

    max_evals = 20  # maximum number of iterations allowed by the algorithm to run

    DYNAMIC_PARAMETERS = OrderedDict([('Hs_ag', hp.uniform('Hs_ag', 0.1, 0.25)),
                                      ('Tcs_set_C', hp.uniform('Tcs_set_C', 24, 26)),
                                      ('Es', hp.uniform('Es', 0.4, 0.6)),
                                      ('Ns', hp.uniform('Ns', 0.4, 0.6)),
                                      ('Occ_m2pax', hp.uniform('Occ_m2pax', 35.0, 45.0)),
                                      ('Vww_lpdpax', hp.uniform('Vww_lpdpax', 25.0, 30.0)),
                                      ('Ea_Wm2', hp.uniform('Ea_Wm2', 1, 2.5)),
                                      ('El_Wm2', hp.uniform('El_Wm2', 1, 2.5))
                                      ])

    results = pd.DataFrame()
    for counter in range(0, max_evals):
        results_it = [counter,
                      trials.trials[counter]['misc']['vals']['SEED'][0],
                      trials.trials[counter]['misc']['vals']['Hs_ag'][0],
                      trials.trials[counter]['misc']['vals']['Tcs_set_C'][0],
                      trials.trials[counter]['misc']['vals']['Ea_Wm2'][0],
                      trials.trials[counter]['misc']['vals']['El_Wm2'][0],
                      trials.trials[counter]['misc']['vals']['Es'][0],
                      trials.trials[counter]['misc']['vals']['Ns'][0],
                      trials.trials[counter]['misc']['vals']['Occ_m2pax'][0],
                      trials.trials[counter]['misc']['vals']['Vww_lpdpax'][0],
                      trials.losses()[counter]
                      ]
        results_it = pd.DataFrame([results_it])
        results = results.append(results_it)
    results.reset_index(drop=True, inplace=True)
    results = pd.concat([results, validation_n_calib, validation_percentage],  axis=1, sort=False).sort_index()

    results.columns = ['ID', 'Hs_ag','Tcs_set_C', 'Ea_Wm2', 'El_Wm2', 'Es',
                       'Ns', 'Occ_m2pax', 'Vww_lpdpax', 'total_buildings_demand']
    project_path = config.project
    output_path = (project_path + r'/output/sensitivity/')

    if not os.path.exists(output_path):
        os.makedirs(output_path)
    file_name = output_path+'sensitivity_results.csv'
    results.to_csv(file_name, index=False)



def main(config):
    """
    This is the main entry point to your script. Any parameters used by your script must be present in the ``config``
    parameter. The CLI will call this ``main`` function passing in a ``config`` object after adjusting the configuration
    to reflect parameters passed on the command line / user interface

    :param cea.config.Configuration config: The configuration for this script, restricted to the scripts parameters.
    :return: None
    """

    project_path = config.project


if __name__ == '__main__':
    main(cea.config.Configuration())
