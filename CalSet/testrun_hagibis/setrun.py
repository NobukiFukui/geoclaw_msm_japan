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

# Need to adjust the date a bit due to weirdness with leap year (I think)
#landfall = datetime.datetime(1979,9,1,18) - datetime.datetime(1979,1,1,0)

# Time Conversions
def days2seconds(days):
    return days * 60.0**2 * 24.0


# Scratch directory for storing topo and dtopo files:
#scratch_dir = os.path.join(os.environ["CLAW"], 'geoclaw', 'scratch')
topodir = os.path.join(os.getcwd(), '..', 'topo')


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
    clawdata.lower[0] = -1062000.0         # west X
    clawdata.upper[0] =   396000.0 -2430.0 # east X
    clawdata.lower[1] =  -862000.0         # south Y
    clawdata.upper[1] =   377300.0 -2430.0 # north Y

    # Number of grid cells:
    clawdata.num_cells[0] = 599 # nx 
    clawdata.num_cells[1] = 509 # ny


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
    clawdata.capa_index = 0 # 0 for cartesian x-y, 2 for spherical lat-lon

    
    
    # -------------
    # Initial time:
    # -------------
    clawdata.t0 = 0.0

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
        clawdata.output_times = [i*3600.0 for i in range(0,122)]

    elif clawdata.output_style == 3:
        # Output every iout timesteps with a total of ntot time steps:
        clawdata.output_step_interval = 1
        clawdata.total_steps = 1
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
    clawdata.dt_initial = 0.02

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
    amrdata.amr_levels_max = 5

    # List of refinement ratios at each level (length at least mxnest-1)
    amrdata.refinement_ratios_x = [3,3,3,3]
    amrdata.refinement_ratios_y = [3,3,3,3]
    amrdata.refinement_ratios_t = [3,3,3,3]


    # Specify type of each aux variable in amrdata.auxtype.
    # This must be a list of length maux, each element of which is one of:
    #   'center',  'capacity', 'xleft', or 'yleft'  (see documentation).

    #amrdata.aux_type = ['center','capacity','yleft','center','center','center','center', 'center', 'center'] # For lon-lat
    amrdata.aux_type = ['center','center','yleft','center','center','center','center', 'center', 'center']  # For X-Y


    # Flag using refinement routine flag2refine rather than richardson error
    amrdata.flag_richardson = False    # use Richardson?
    amrdata.flag2refine = True

    # steps to take on each level L between regriddings of level L+1:
    amrdata.regrid_interval = 3

    # width of buffer zone around flagged points:
    # (typically the same as regrid_interval so waves don't escape):
    amrdata.regrid_buffer_width  = 2

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
    
    # Target simulation domain

    # gauges 
    #rundata.gaugedata.gauges.append([1, 2.5, 0.0, 0., 1.e10])
    rundata.gaugedata.gauges.append([1, -148259.0, -152271.0, 0., 1.e10]) # Omaezaki
    rundata.gaugedata.gauges.append([2, -120163.0, -108297.0, 0., 1.e10]) # Shimizu
    rundata.gaugedata.gauges.append([3,  -89128.0, -108677.0, 0., 1.e10]) # Uchiura
    rundata.gaugedata.gauges.append([4,  -87745.0, -155540.0, 0., 1.e10]) # Irozaki
    rundata.gaugedata.gauges.append([5,  -26157.0, -216277.0, 0., 1.e10]) # Miyakejima
    rundata.gaugedata.gauges.append([6,  -41183.0, -132450.0, 0., 1.e10]) # Okada
    rundata.gaugedata.gauges.append([7,  -62196.0,  -84840.0, 0., 1.e10]) # Odawara
    rundata.gaugedata.gauges.append([8,   -6036.0,  -38828.0, 0., 1.e10]) # Tokyo
    rundata.gaugedata.gauges.append([9,   -2430.0, -122612.0, 0., 1.e10]) # Mera
    rundata.gaugedata.gauges.append([10,  19237.0,  -47900.0, 0., 1.e10]) # Chibako
    #(-148259.69955929325, -152271.87440424366)
    #(-120163.33915535029, -108297.50570064224)
    #(-86698.87075035876, -108677.38864516467)
    #(-90175.88456599312, -153020.6799371466)
    #(-26157.766996316208, -216277.23930901662)
    #(-41183.69595472718, -134880.70228973124)
    #(-62196.928931328344, -84840.65226609632)
    #(-6036.757078895429, -38828.58597665606)
    #(-3.254854452358613e-8, -120182.73355006939)



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
    #geo_data.coordinate_system = 2 # lonlat
    geo_data.coordinate_system = 1 # XY
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
    refine_data.wave_tolerance = 0.20
    refine_data.speed_tolerance = [0.25, 0.50, 0.75, 1.00]

    refine_data.deep_depth = 3.0e3
    refine_data.max_level_deep = 2
    refine_data.variable_dt_refinement_ratios = True

    # == settopo.data values ==
    topo_data = rundata.topo_data
    topo_data.topofiles = []
    # for topography, append lines of the form
    #   [topotype, minlevel, maxlevel, t1, t2, fname]
    # See regions for control over these regions, need better bathy data for the
    # smaller domains
    topo_data.topofiles.append([3, 1, 1, rundata.clawdata.t0, rundata.clawdata.tfinal, os.path.join(topodir,'topo_01L_mask.dat')])
    topo_data.topofiles.append([3, 1, 2, rundata.clawdata.t0, rundata.clawdata.tfinal, os.path.join(topodir,'topo_02_mask.dat')])
    topo_data.topofiles.append([3, 1, 3, rundata.clawdata.t0, rundata.clawdata.tfinal, os.path.join(topodir,'topo_03_mask.dat')])
    topo_data.topofiles.append([3, 1, 4, rundata.clawdata.t0, rundata.clawdata.tfinal, os.path.join(topodir,'topo_04_mask.dat')])
    topo_data.topofiles.append([3, 1, 5, rundata.clawdata.t0, rundata.clawdata.tfinal, os.path.join(topodir,'topo_05.dat')])

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
    force_dry = ForceDry()
    force_dry.tend = 1e10
    force_dry.fname = os.path.join(topodir, 'force_dry_init_05.dat')
    rundata.qinit_data.force_dry_list.append(force_dry)

    # == setfixedgrids.data values ==
    rundata.fixed_grid_data.fixedgrids = []
    # for fixed grids append lines of the form
    # [t1,t2,noutput,x1,x2,y1,y2,xpoints,ypoints,\
    #  ioutarrivaltimes,ioutsurfacemax]

    # == fgmax.data values ==
    fgmax_files = rundata.fgmax_data.fgmax_files
    # Points on a uniform 2d grid:
    # Domain 4
    fg = fgmax_tools.FGmaxGrid()
    fg.point_style = 2  # uniform rectangular x-y grid
    fg.dx = 90.0           # desired resolution of fgmax grid
    fg.x1 = -20790.0
    fg.x2 =  28710.0 - fg.dx
    fg.y1 = -82690.0
    fg.y2 = -19690.0 - fg.dx
    fg.min_level_check = 1 # which levels to monitor max on
    fg.arrival_tol = 1.0e-1
    fg.tstart_max = 3600.0*48.0    # just before wave arrives
    fg.tend_max = 1.e10    # when to stop monitoring max values
    fg.dt_check = 60.0     # how often to update max values
    fg.interp_method = 0   # 0 ==> pw const in cells, recommended
    rundata.fgmax_data.fgmax_grids.append(fg)  # written to fgmax_grids.data
    # Domain 5
    fg = fgmax_tools.FGmaxGrid()
    fg.point_style = 2  # uniform rectangular x-y grid
    fg.dx = 30.0           # desired resolution of fgmax grid
    fg.x1 = -11730.0
    fg.x2 =   7770.0 - fg.dx
    fg.y1 = -49630.0
    fg.y2 = -19930.0 - fg.dx
    fg.min_level_check = 1 # which levels to monitor max on
    fg.arrival_tol = 1.0e-1
    fg.tstart_max = 3600.0*48.0    # just before wave arrives
    fg.tend_max = 1.e10    # when to stop monitoring max values
    fg.dt_check = 60.0     # how often to update max values
    fg.interp_method = 0   # 0 ==> pw const in cells, recommended
    rundata.fgmax_data.fgmax_grids.append(fg)  # written to fgmax_grids.data
    # num_fgmax_val
    rundata.fgmax_data.num_fgmax_val = 5  # 1 to save depth, 2 to save depth and speed, and 5 to Save depth, speed, momentum, momentum flux and hmin

    # ================
    #  Set Surge Data
    # ================
    data = rundata.surge_data

    # Source term controls - These are currently not respected
    data.wind_forcing = True
    #data.drag_law = 1
    data.drag_law = 4 # Mitsuyasu & Kusaba no limit drag coeff
    data.pressure_forcing = True

    # AMR parameters
    data.wind_refine = False # m/s
    data.R_refine = False  # m
    
    # Storm parameters
    #data.storm_type = 1 # Type of storm
    data.storm_type = -1 # Explicit storm fields. See ./wrf_storm_module.f90
    data.storm_specification_type = 'WRF'
    #data.landfall = 3600.0
    data.display_landfall_time = True

    # Storm type 2 - Idealized storm track
    data.storm_file = os.path.join(os.getcwd(),'../rcm/')

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
