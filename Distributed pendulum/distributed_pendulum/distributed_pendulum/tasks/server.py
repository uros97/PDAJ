from datetime import datetime
import os
import socket
import subprocess
import time
import csv


from celery import chain, chord
from celery.exceptions import Reject
import numpy as np
import tables as tb

from ..app import app
from .worker import solve


## Recording the experiment status

def get_experiment_status_filename(status):
    return os.path.join(app.conf.STATUS_DIR, status)

def get_experiment_status_time():
    """Get the current local date and time, in ISO 8601 format (microseconds and TZ removed)"""
    return datetime.now().replace(microsecond=0).isoformat()

@app.task
def record_experiment_status(status):
    with open(get_experiment_status_filename(status), 'w') as fp:
        fp.write(get_experiment_status_time() + '\n')


## Seeding the computations

@app.task
def seed_computations(ignore_result=True):
    if os.path.exists(get_experiment_status_filename('started')):
        raise Reject('Computations have already been seeded!')

    record_experiment_status.si('started').delay()
    
    chord(
        simulate_pendulum(),
        record_experiment_status.si('completed')
    ).delay()


def gen_simulation_model_params(theta_resolution, L1, L2, m1, m2, tmax, dt):
    search_space = np.linspace(0, 2*np.pi, theta_resolution)
    for theta1_init in search_space:
        for theta2_init in search_space:
            # Initial conditions: theta1_init, dtheta1_init/dt, theta2_init, dtheta2_init/dt.
            y0 = np.array([theta1_init, 0, theta2_init, 0])

            yield theta1_init, theta2_init, L1, L2, m1, m2, tmax, dt, y0
           
@app.task
def simulate_pendulum():
    theta_resolution = app.conf.PENDULUM_RESOLUTION
    dt = app.conf.PENDULUM_DT
    tmax = app.conf.PENDULUM_TMAX
    L1 = app.conf.PENDULUM_L1
    L2 = app.conf.PENDULUM_L2
    m1 = app.conf.PENDULUM_M1
    m2 = app.conf.PENDULUM_M2

    return chord(
        (solve.s(theta1_init, theta2_init, L1, L2, m1, m2, tmax, dt, y0) for theta1_init, theta2_init, L1, L2, m1, m2, tmax, dt, y0 in gen_simulation_model_params(theta_resolution, L1, L2, m1, m2, tmax, dt)),
        write_to_csv.s()
    )

@app.task
def write_to_csv(results):
        results_dir = app.conf.RESULTS_DIR
        filename = os.path.join(results_dir, "distributed36.csv")

        with open(filename, 'w') as csvfile:
            seqwriter = csv.writer(csvfile, delimiter = ',')
            seqwriter.writerow(['theta1_init', 'theta2_init', 'theta1', 'theta2'])
            seqwriter.writerows(results)

