import argparse
import numpy as np
import csv
from scipy.integrate import odeint
from multiprocessing import Pool
from functools import partial


DEFAULT_RESOLUTION = 6
DEFAULT_TMAX = 30
DEFAULT_DT = 0.01

DEFAULT_L1 = 1
DEFAULT_L2 = 1
DEFAULT_M1 = 1
DEFAULT_M2 = 1

# The gravitational acceleration (m.s-2).
g = 9.81


def deriv(y, t, L1, L2, m1, m2):
    """Return the first derivatives of y = theta1, z1, theta2, z2."""
    theta1, z1, theta2, z2 = y

    c, s = np.cos(theta1-theta2), np.sin(theta1-theta2)

    theta1dot = z1
    z1dot = (m2*g*np.sin(theta2)*c - m2*s*(L1*z1**2*c + L2*z2**2) -
             (m1+m2)*g*np.sin(theta1)) / L1 / (m1 + m2*s**2)
    theta2dot = z2
    z2dot = ((m1+m2)*(L1*z1**2*s - g*np.sin(theta2) + g*np.sin(theta1)*c) +
             m2*L2*z2**2*s*c) / L2 / (m1 + m2*s**2)
    return theta1dot, z1dot, theta2dot, z2dot

def solve(L1, L2, m1, m2, tmax, dt, y0):
    t = np.arange(0, tmax+dt, dt)

    # Do the numerical integration of the equations of motion
    y = odeint(deriv, y0, t, args=(L1, L2, m1, m2))
    theta1, theta2 = y[:,0], y[:,2]

    # Convert to Cartesian coordinates of the two bob positions.
    x1 = L1 * np.sin(theta1)
    y1 = -L1 * np.cos(theta1)
    x2 = x1 + L2 * np.sin(theta2)
    y2 = y1 - L2 * np.cos(theta2)

    return y0[0], y0[2], theta1, theta2, x1, y1, x2, y2

def gen_simulation_model_params(theta_resolution):
    search_space = np.linspace(0, 2*np.pi, theta_resolution)
    for theta1_init in search_space:
        for theta2_init in search_space:
            yield theta1_init, theta2_init

def simulate_pendulum_parallel(theta_resolution, dt=DEFAULT_DT, tmax=DEFAULT_TMAX, L1=DEFAULT_L1, L2=DEFAULT_L2, m1=DEFAULT_M1, m2=DEFAULT_M2):
        with Pool() as pool:
            partial_solve = partial(solve, L1, L2, m1, m2, tmax, dt)
            results = pool.imap(
                partial_solve,
                (
                    np.array([theta1_init, 0, theta2_init, 0])
                    for theta1_init, theta2_init in gen_simulation_model_params(theta_resolution)
                ), 
                1
            )
            for theta1_init, theta2_init, theta1, theta2, x1, y1, x2, y2 in results:  
                yield theta1_init, theta2_init, theta1[-1], theta2[-1]


def write_to_csv(filename, results):
        with open(filename, 'w', newline = '\n') as csvfile:
            seqwriter = csv.writer(csvfile, delimiter = ',')
            seqwriter.writerow(['theta1_init', 'theta2_init', 'theta1', 'theta2'])
            seqwriter.writerows(results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'results_file',
        help="Filename where the results will be stored, in CSV format"
    )
    parser.add_argument(
        '-r',
        '--resolution',
        metavar='NUM',
        type=int,
        default=DEFAULT_RESOLUTION,
        help="Resolution, %d by default" % DEFAULT_RESOLUTION
    )
    parser.add_argument(
        '--tmax',
        metavar='NUM',
        type=float,
        default=DEFAULT_TMAX,
        help="Simulation time, %f by default" % DEFAULT_TMAX
    )
    parser.add_argument(
        '--dt',
        metavar='NUM',
        type=float,
        default=DEFAULT_DT,
        help="Simulation time step, %f by default" % DEFAULT_DT
    )
    args = parser.parse_args()
    results = simulate_pendulum_parallel(
        theta_resolution=args.resolution,
        dt=args.dt,
        tmax=args.tmax,
    )

    write_to_csv(args.results_file, results)
    

if __name__ == '__main__':
    main()