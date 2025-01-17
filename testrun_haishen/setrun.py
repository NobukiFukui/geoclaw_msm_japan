# encoding: utf-8
"""
Module to set up run time parameters for Clawpack.

The values set in the function setrun are then written out to data files
that will be read in by the Fortran code.

"""

from __future__ import absolute_import
from __future__ import print_function

import os
import datetime
import shutil
import gzip

import numpy as np

from clawpack.geoclaw.surge.storm import Storm
import clawpack.clawutil as clawutil
from clawpack.geoclaw import fgmax_tools
from clawpack.geoclaw.data import ForceDry
from clawpack.geoclaw import topotools


# Time Conversions
def days2seconds(days):
    return days * 60.0**2 * 24.0

# Scratch directory for storing topo and dtopo files:
topodir = os.path.join(os.getcwd(), '..', 'topo')
# topolist
topoflist = {
             "GEBCO2020":"gebco_2020_n60.0_s0.0_w105.0_e165.0_landmask.asc",
             #"Z01_2430_01":"depth_2430-01_zone01_lonlat_5mWall_ver2.asc",
             #"Z01_0810_02":"depth_0810-02_zone01_lonlat_5mWall_ver2.asc",
             #"Z01_0270_03":"depth_0270-03_zone01_lonlat_5mWall_ver2.asc",
             #"Z01_0270_04":"depth_0270-04_zone01_lonlat_5mWall_ver2.asc",
             }

# ------------------------------
def setrun(claw_pkg='geoclaw'):
#------------------------------

    """
    Define the parameters used for running Clawpack.

    INPUT:
        claw_pkg expected to be "geoclaw" for this setrun.

    OUTPUT:
        rundata - object of class ClawRunData

    """

    from clawpack.clawutil import data

    assert claw_pkg.lower() == 'geoclaw',  "Expected claw_pkg = 'geoclaw'"

    num_dim = 2
    rundata = data.ClawRunData(claw_pkg, num_dim)

    #------------------------------------------------------------------
    # Problem-specific parameters to be written to setprob.data:
    #------------------------------------------------------------------
    
    #probdata = rundata.new_UserData(name='probdata',fname='setprob.data')

    #------------------------------------------------------------------
    # Standard Clawpack parameters to be written to claw.data:
    #   (or to amr2ez.data for AMR)
    #------------------------------------------------------------------
    clawdata = rundata.clawdata  # initialized when rundata instantiated


    # Set single grid parameters first.
    # See below for AMR parameters.


    # ---------------
    # Spatial domain:
    # ---------------

    # Number of space dimensions:
    clawdata.num_dim = num_dim

    # Lower and upper edge of computational domain:
    clawdata.lower[0] = 120.0    # west longitude
    clawdata.upper[0] = 150.0   # east longitude
    clawdata.lower[1] = 22.0    # south latitude
    clawdata.upper[1] = 52.0   # north latitude

    # Number of grid cells
    clawdata.num_cells[0] = 300 # nx
    clawdata.num_cells[1] = 300 # ny


    # ---------------
    # Size of system:
    # ---------------

    # Number of equations in the system:
    clawdata.num_eqn = 3

    # Number of auxiliary variables in the aux array (initialized in setaux)
    # First three are from shallow GeoClaw, fourth is friction and last 3 are
    # storm fields
    clawdata.num_aux = 3 + 1 + 3

    # Index of aux array corresponding to capacity function, if there is one:
    clawdata.capa_index = 2 # 0 for cartesian x-y, 2 for spherical lat-lon
    
    
    # -------------
    # Initial time:
    # -------------
    clawdata.t0 = 0.0                # for WRF input
    # clawdata.t0 = -1.29600000e+05  # for TC model

    # Restart from checkpoint file of a previous run?
    # If restarting, t0 above should be from original run, and the
    # restart_file 'fort.chkNNNNN' specified below should be in 
    # the OUTDIR indicated in Makefile.

    clawdata.restart = False               # True to restart from prior results
    clawdata.restart_file = 'fort.chk00006'  # File to use for restart data

    # -------------
    # Output times:
    #--------------

    # Specify at what times the results should be written to fort.q files.
    # Note that the time integration stops after the final output time.
    # The solution at initial time t0 is always written in addition.

    clawdata.output_style = 2
    clawdata.tfinal = days2seconds(5) + 3600.0

    if clawdata.output_style==1:
        # Output nout frames at equally spaced times up to tfinal:
        clawdata.num_output_times = 121
        clawdata.output_t0 = True  # output at initial (or restart) time?

    elif clawdata.output_style == 2:
        # Specify a list of output times.
        #clawdata.output_times = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
        # clawdata.output_times = [i*3600.0 for i in range(0,120)]
        clawdata.output_times = [i*1200.0 for i in range(0,360)]
        #clawdata.output_times = [i*600.0 for i in range(0,13)]

    elif clawdata.output_style == 3:
        # Output every iout timesteps with a total of ntot time steps:
        clawdata.output_step_interval = 1
        clawdata.total_steps = 100
        clawdata.output_t0 = True
        

    clawdata.output_format = 'ascii'      # 'ascii' or 'netcdf' 
    clawdata.output_q_components = 'all'   # could be list such as [True,True]
    clawdata.output_aux_components = 'all'
    clawdata.output_aux_onlyonce = False    # output aux arrays only at t0



    # ---------------------------------------------------
    # Verbosity of messages to screen during integration:
    # ---------------------------------------------------

    # The current t, dt, and cfl will be printed every time step
    # at AMR levels <= verbosity.  Set verbosity = 0 for no printing.
    #   (E.g. verbosity == 2 means print only on levels 1 and 2.)
    clawdata.verbosity = 1



    # --------------
    # Time stepping:
    # --------------

    # if dt_variable==1: variable time steps used based on cfl_desired,
    # if dt_variable==0: fixed time steps dt = dt_initial will always be used.
    clawdata.dt_variable = True

    # Initial time step for variable dt.
    # If dt_variable==0 then dt=dt_initial for all steps:
    clawdata.dt_initial = 0.5

    # Max time step to be allowed if variable dt used:
    clawdata.dt_max = 1e+99
    #clawdata.dt_max = 6.0e+2

    # Desired Courant number if variable dt used, and max to allow without
    # retaking step with a smaller dt:
    clawdata.cfl_desired = 0.50
    clawdata.cfl_max = 0.70

    # Maximum number of time steps to allow between output times:
    clawdata.steps_max = 500000




    # ------------------
    # Method to be used:
    # ------------------

    # Order of accuracy:  1 => Godunov,  2 => Lax-Wendroff plus limiters
    clawdata.order = 1
    
    # Use dimensional splitting? (not yet available for AMR)
    clawdata.dimensional_split = 'unsplit'
    
    # For unsplit method, transverse_waves can be 
    #  0 or 'none'      ==> donor cell (only normal solver used)
    #  1 or 'increment' ==> corner transport of waves
    #  2 or 'all'       ==> corner transport of 2nd order corrections too
    clawdata.transverse_waves = 1

    # Number of waves in the Riemann solution:
    clawdata.num_waves = 3
    
    # List of limiters to use for each wave family:  
    # Required:  len(limiter) == num_waves
    # Some options:
    #   0 or 'none'     ==> no limiter (Lax-Wendroff)
    #   1 or 'minmod'   ==> minmod
    #   2 or 'superbee' ==> superbee
    #   3 or 'mc'       ==> MC limiter
    #   4 or 'vanleer'  ==> van Leer
    clawdata.limiter = ['mc', 'mc', 'mc']

    clawdata.use_fwaves = True    # True ==> use f-wave version of algorithms
    
    # Source terms splitting:
    #   src_split == 0 or 'none'    ==> no source term (src routine never called)
    #   src_split == 1 or 'godunov' ==> Godunov (1st order) splitting used, 
    #   src_split == 2 or 'strang'  ==> Strang (2nd order) splitting used,  not recommended.
    clawdata.source_split = 'godunov'
    # clawdata.source_split = 'strang'


    # --------------------
    # Boundary conditions:
    # --------------------

    # Number of ghost cells (usually 2)
    clawdata.num_ghost = 4

    # Choice of BCs at xlower and xupper:
    #   0 => user specified (must modify bcN.f to use this option)
    #   1 => extrapolation (non-reflecting outflow)
    #   2 => periodic (must specify this at both boundaries)
    #   3 => solid wall for systems where q(2) is normal velocity

    clawdata.bc_lower[0] = 'extrap' # west
    clawdata.bc_upper[0] = 'extrap' # east 

    clawdata.bc_lower[1] = 'extrap' # south
    clawdata.bc_upper[1] = 'extrap' # north

    # Specify when checkpoint files should be created that can be
    # used to restart a computation.

    clawdata.checkpt_style = 0

    if clawdata.checkpt_style == 0:
        # Do not checkpoint at all
        pass

    elif np.abs(clawdata.checkpt_style) == 1:
        # Checkpoint only at tfinal.
        pass

    elif np.abs(clawdata.checkpt_style) == 2:
        # Specify a list of checkpoint times.
        clawdata.checkpt_times = [0.1, 0.15]

    elif np.abs(clawdata.checkpt_style) == 3:
        # Checkpoint every checkpt_interval timesteps (on Level 1)
        # and at the final time.
        clawdata.checkpt_interval = 5


    # ---------------
    # AMR parameters:
    # ---------------
    amrdata = rundata.amrdata

    # max number of refinement levels:
    amrdata.amr_levels_max = 2

    # List of refinement ratios at each level (length at least mxnest-1)
    amrdata.refinement_ratios_x = [6,2,2]
    amrdata.refinement_ratios_y = [6,2,2]
    amrdata.refinement_ratios_t = [6,2,2]


    # Specify type of each aux variable in amrdata.auxtype.
    # This must be a list of length maux, each element of which is one of:
    #   'center',  'capacity', 'xleft', or 'yleft'  (see documentation).

    amrdata.aux_type = ['center','capacity','yleft','center','center','center','center', 'center', 'center'] # For lon-lat
    # amrdata.aux_type = ['center','center','yleft','center','center','center','center', 'center', 'center']  # For X-Y


    # Flag using refinement routine flag2refine rather than richardson error
    amrdata.flag_richardson = False    # use Richardson?
    amrdata.flag2refine = True

    # steps to take on each level L between regriddings of level L+1:
    amrdata.regrid_interval = 3

    # width of buffer zone around flagged points:
    # (typically the same as regrid_interval so waves don't escape):
    amrdata.regrid_buffer_width  = 3

    # clustering alg. cutoff for (# flagged pts) / (total # of cells refined)
    # (closer to 1.0 => more small grids may be needed to cover flagged cells)
    amrdata.clustering_cutoff = 0.700000

    # print info about each regridding up to this level:
    amrdata.verbosity_regrid = 0  


    #  ----- For developers ----- 
    # Toggle debugging print statements:
    amrdata.dprint = False      # print domain flags
    amrdata.eprint = False      # print err est flags
    amrdata.edebug = False      # even more err est flags
    amrdata.gprint = False      # grid bisection/clustering
    amrdata.nprint = True       # proper nesting output
    amrdata.pprint = False      # proj. of tagged points
    amrdata.rprint = False      # print regridding summary
    amrdata.sprint = False      # space/memory output
    amrdata.tprint = True       # time step reporting each level
    amrdata.uprint = False      # update/upbnd reporting
    
    # More AMR parameters can be set -- see the defaults in pyclaw/data.py

    # == setregions.data values ==
    #rundata.regiondata.regions = []
    regions = rundata.regiondata.regions
    # to specify regions of refinement append lines of the form
    #  [minlevel,maxlevel,t1,t2,x1,x2,y1,y2]
    regions.append([1, 2, clawdata.t0, clawdata.tfinal, clawdata.lower[0], clawdata.upper[0], clawdata.lower[1], clawdata.upper[1]])
    topo_file = topotools.Topography(os.path.join(topodir, topoflist['GEBCO2020']), topo_type=3)
    #regions.append([1, 3, clawdata.t0, clawdata.tfinal, clawdata.lower[0], clawdata.upper[0], clawdata.lower[1], clawdata.upper[1]])
    #topo_file = topotools.Topography(os.path.join(topodir, topoflist['Z01_2430_01']), topo_type=3)
    #regions.append([1, 4, clawdata.t0, clawdata.tfinal, clawdata.lower[0], clawdata.upper[0], clawdata.lower[1], clawdata.upper[1]])
    #topo_file = topotools.Topography(os.path.join(topodir, topoflist['Z01_0810_02']), topo_type=3)

    
    # Target simulation domain
    gauges = rundata.gaugedata.gauges
    gauges.append([1, 130.22, 33.00, 0., 1.e10]) # Oura
    gauges.append([2, 130.20, 32.57, 0., 1.e10]) # Kuchinotsu
    gauges.append([3, 130.25, 33.10, 0., 1.e10]) # Saga
    gauges.append([4, 130.01, 32.47, 0., 1.e10]) # Reihoku
    gauges.append([5, 128.95, 32.70, 0., 1.e10]) # Fukue
    gauges.append([6, 130.60, 31.10, 0., 1.e10]) # Kagoshima
    gauges.append([7, 130.30, 31.20, 0., 1.e10]) # Makurazaki
    gauges.append([8, 131.42, 31.58, 0., 1.e10]) # Aburatsu
    gauges.append([9, 132.00, 32.97, 0., 1.e10]) # Saeki
    gauges.append([10, 132.97, 32.60, 0., 1.e10]) # Tosa-Shimizu
    gauges.append([11, 132.43, 33.25, 0., 1.e10]) # Uwajima
    gauges.append([12, 132.50, 33.80, 0., 1.e10]) # Matsuyama
    gauges.append([13, 131.04, 34.00, 0., 1.e10]) # Shimonoseki


    #------------------------------------------------------------------
    # GeoClaw specific parameters:
    #------------------------------------------------------------------
    rundata = setgeo(rundata)

    return rundata
    # end of function setrun
    # ----------------------


#-------------------
def setgeo(rundata):
#-------------------
    """
    Set GeoClaw specific runtime parameters.
    For documentation see ....
    """

    try:
        geo_data = rundata.geo_data
    except:
        print("*** Error, this rundata has no geo_data attribute")
        raise AttributeError("Missing geo_data attribute")
       
    # == Physics ==
    geo_data.gravity = 9.81
    geo_data.coordinate_system = 2 # lonlat
    # geo_data.coordinate_system = 1 # XY
    geo_data.earth_radius = 6367.5e3
    geo_data.rho = 1025.0
    geo_data.rho_air = 1.15
    geo_data.ambient_pressure = 101.3e3 # Nominal atmos pressure

    # == Forcing Options
    geo_data.coriolis_forcing = False
    geo_data.friction_forcing = True
    geo_data.manning_coefficient = 0.025 # Overridden below
    geo_data.friction_depth = 1e10

    # == Algorithm and Initial Conditions ==
    geo_data.sea_level = 0.0
    geo_data.dry_tolerance = 1.e-2

    # Refinement Criteria
    refine_data = rundata.refinement_data
    refine_data.wave_tolerance = 1.0
    refine_data.speed_tolerance = 1.0 #[0.25, 0.50, 0.75, 1.00]

    refine_data.deep_depth = 3.0e3
    refine_data.max_level_deep = 1
    refine_data.variable_dt_refinement_ratios = True

    # == settopo.data values ==
    topo_data = rundata.topo_data
    topo_data.topofiles = []
    # for topography, append lines of the form
    #   [topotype, minlevel, maxlevel, t1, t2, fname]
    # See regions for control over these regions, need better bathy data for the
    # smaller domains
    topo_data.topofiles.append([3, 1, 4, rundata.clawdata.t0, rundata.clawdata.tfinal, os.path.join(topodir, topoflist['GEBCO2020'])])

    # == setdtopo.data values ==
    dtopo_data = rundata.dtopo_data
    dtopo_data.dtopofiles = []
    # for moving topography, append lines of the form :   (<= 1 allowed for now!)
    #   [topotype, minlevel,maxlevel,fname]

    # == setqinit.data values ==
    rundata.qinit_data.qinit_type = 0
    rundata.qinit_data.qinitfiles = []
    # for qinit perturbations, append lines of the form: (<= 1 allowed for now!)
    #   [minlev, maxlev, fname]

    # NEW feature to force dry land some locations below sea level:
    # force_dry = ForceDry()
    # force_dry.tend = 1e10
    # force_dry.fname = os.path.join(topodir, 'force_dry_init_05.dat')
    # rundata.qinit_data.force_dry_list.append(force_dry)

    # == setfixedgrids.data values ==
    rundata.fixed_grid_data.fixedgrids = []
    # for fixed grids append lines of the form
    # [t1,t2,noutput,x1,x2,y1,y2,xpoints,ypoints,\
    #  ioutarrivaltimes,ioutsurfacemax]

    # == fgmax.data values ==
    fgmax_files = rundata.fgmax_data.fgmax_files
    # Points on a uniform 2d grid:

    ## 2430
    #topo_file = topotools.Topography(os.path.join(topodir, topoflist['Z01_2430_01']), topo_type=3)
    fg = fgmax_tools.FGmaxGrid()
    fg.point_style = 2  # uniform rectangular x-y grid
    fg.dx = 1/10        # desired resolution of fgmax grid
    fg.x1 = 125
    fg.x2 = 145
    fg.y1 = 25
    fg.y2 = 45
    fg.min_level_check = 1 # which levels to monitor max on
    fg.arrival_tol = 1.0e-1
    fg.tstart_max = 3600.0*24    # just before wave arrives
    fg.tend_max = 1.e10    # when to stop monitoring max values
    fg.dt_check = 60.0     # how often to update max values
    fg.interp_method = 0   # 0 ==> pw const in cells, recommended
    rundata.fgmax_data.fgmax_grids.append(fg)  # written to fgmax_grids.data

    ### 810
    #topo_file = topotools.Topography(os.path.join(topodir, topoflist['Z01_0810_02']), topo_type=3)
    #fg = fgmax_tools.FGmaxGrid()
    #fg.point_style = 2  # uniform rectangular x-y grid
    #fg.dx = topo_file.delta[0]        # desired resolution of fgmax grid
    #fg.x1 = topo_file.x[0]
    #fg.x2 = topo_file.x[-1]
    #fg.y1 = topo_file.y[0]
    #fg.y2 = topo_file.y[-1]
    #fg.min_level_check = 1 # which levels to monitor max on
    #fg.arrival_tol = 1.0e-1
    #fg.tstart_max = 3600.0*24    # just before wave arrives
    #fg.tend_max = 1.e10    # when to stop monitoring max values
    #fg.dt_check = 60.0     # how often to update max values
    #fg.interp_method = 0   # 0 ==> pw const in cells, recommended
    #rundata.fgmax_data.fgmax_grids.append(fg)  # written to fgmax_grids.data

    ### 1/360
    #topo_file = topotools.Topography(os.path.join(topodir, topoflist['Z01_0270_03']), topo_type=3)
    #fg = fgmax_tools.FGmaxGrid()
    #fg.point_style = 2  # uniform rectangular x-y grid
    #fg.dx = topo_file.delta[0]        # desired resolution of fgmax grid
    #fg.x1 = topo_file.x[0]
    #fg.x2 = topo_file.x[-1]
    #fg.y1 = topo_file.y[0]
    #fg.y2 = topo_file.y[-1]
    #fg.min_level_check = 1 # which levels to monitor max on
    #fg.arrival_tol = 1.0e-1
    #fg.tstart_max = 0.0    # just before wave arrives
    #fg.tend_max = 1.e10    # when to stop monitoring max values
    #fg.dt_check = 10.0     # how often to update max values
    #fg.interp_method = 0   # 0 ==> pw const in cells, recommended
    #rundata.fgmax_data.fgmax_grids.append(fg)  # written to fgmax_grids.data

    ### 1/360
    #topo_file = topotools.Topography(os.path.join(topodir, topoflist['Z01_0270_04']), topo_type=3)
    #fg = fgmax_tools.FGmaxGrid()
    #fg.point_style = 2  # uniform rectangular x-y grid
    #fg.dx = topo_file.delta[0]        # desired resolution of fgmax grid
    #fg.x1 = topo_file.x[0]
    #fg.x2 = topo_file.x[-1]
    #fg.y1 = topo_file.y[0]
    #fg.y2 = topo_file.y[-1]
    #fg.min_level_check = 1 # which levels to monitor max on
    #fg.arrival_tol = 1.0e-1
    #fg.tstart_max = 0.0    # just before wave arrives
    #fg.tend_max = 1.e10    # when to stop monitoring max values
    #fg.dt_check = 10.0     # how often to update max values
    #fg.interp_method = 0   # 0 ==> pw const in cells, recommended
    #rundata.fgmax_data.fgmax_grids.append(fg)  # written to fgmax_grids.data


    # num_fgmax_val
    rundata.fgmax_data.num_fgmax_val = 5  # 1 to save depth, 2 to save depth and speed, and 5 to Save depth, speed, momentum, momentum flux and hmin

    # ================
    #  Set Surge Data
    # ================
    data = rundata.surge_data

    # Source term controls - These are currently not respected
    data.wind_forcing = True
    data.drag_law = 1
    #data.drag_law = 4 # Honda & Mitsuyasu no limit drag coeff
    data.pressure_forcing = True

    # AMR parameters
    data.wind_refine = [20.0,30.0,40.0] # m/s
    data.R_refine = False  # m
    
    # Storm parameters
    data.storm_type = -2 # Type of storm
    data.storm_specification_type = 'WRF'
    #data.landfall = 3600.0
    data.display_landfall_time = True

    # Storm type 2 - Idealized storm track
    data.storm_file = os.path.join(os.getcwd(),'./')

    # Calculate landfall time - Need to specify as the file above does not

    # =======================
    #  Set Variable Friction
    # =======================
    data = rundata.friction_data

    # Variable friction
    data.variable_friction = True

    # Region based friction
    # Entire domain
    data.friction_regions.append([rundata.clawdata.lower, 
                                  rundata.clawdata.upper,
                                  [np.infty,0.0,-np.infty],
                                  [0.030, 0.022]])
    
    # La-Tex Shelf
    #data.friction_regions.append([(-98, 25.25), (-90, 30),
    #                              [np.infty,-10.0,-200.0,-np.infty],
    #                              [0.030, 0.012, 0.022]])

    return rundata
    # end of function setgeo
    # ----------------------


if __name__ == '__main__':
    # Set up run-time parameters and write all data files.
    import sys
    if len(sys.argv) == 2:
        rundata = setrun(sys.argv[1])
    else:
        rundata = setrun()

    rundata.write()
