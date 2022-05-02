import numpy as np
import numpy.random as random
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy.spatial.distance import pdist, squareform

"""
All particles are considered to have the same constant parameters i.e. mass, radius.
Initial speeds are determined by temperature, from which the speeds are calculated by thermal velocity equation.

"""

class GasSimulation3d:

    def __init__(self, particlesCount=45, mass=5e-20, effectiveRadius=2e-10, volume=1e-23, T=300):
        """
        Initializing starting parameters
        """
        self.partCount = particlesCount  # the amount of particles in simulation
        self.mass = mass  # the mass of any particle
        self.radius = effectiveRadius  # radius of the molecule i.e. distance at which particles will start colliding
        self.volume = volume  # volume of the observed chamber
        self.temp = T  # average temperature of the gas
        self.pos = np.zeros((self.partCount, 3))  # array which will contain particles coordinates
        self.vel = np.zeros((self.partCount, 3))  # array which will contain particles velocities
        self.particleCell = {}
        self.cubicParts1 = int(np.floor(self.partCount ** (1 / 3)))  # created for optimizing future calculations
        self.cubicParts2 = (self.cubicParts1 ** 2)  # created for optimizing future calculations

        """
        Calculating needed parameters from initial conditions.
        """
        self.b = self.partCount * ((4 / 3) * np.pi * (self.radius ** 3))  # idk what this is i forgot
        self.sideLength = (volume ** (1 / 3))  # length of the side of observed chamber
        self.velNormalized = (3 * 1.87e-23 * self.temp / self.mass) ** (1 / 2)  # root mean square of speed of molecules
        self.SetParticles()  # initializing particle initializing method
        self.SetGraphs()  # initializing graph initializing method

        self.partBelonging = np.zeros(self.cubicParts1 ** 3, 7)  # this array is explained in 'Step'
        # calcualting and storing cells borders
        cellLength = self.sideLength / self.cubicParts1 # the length of a side of a cell
        for i in range(self.cubicParts1 ** 3):
            for j in range(3):
                self.partBelonging[i, 2 * j] = cellLength * i
                self.partBelonging[i, 2 * j + 1] = cellLength * (i + 1)

    def SetParticles(self):
        """
        This module places particles inside the chamber and assigns velocities to them. Particles are placed evenly.
        This is done so that the molecules don't spawn inside of each other or don't spawn very close in order to slow
        down the process of converging to Maxwell distribution.
        """

        """
        Calculating positions of the edges of the grid inside the chamber with extra space near walls taken into account
        """
        dists = np.linspace(self.radius * 5, self.sideLength - self.radius * 5, int(np.floor(self.partCount ** (1 / 3))))

        """
        Assigning particles to cells.
        If the amount of particles n is not a perfect cube, we round it down to a nearest cube m ** 3, create a grid
        inside of a chamber with side length of m. Then we assign particles into this grid one by one. Coordinates
        matrix has a format of [[x_1, y_1, z_1]
                                [x_2, y_2, z_2]
                                    ......
                                [x_n, y_n, z_n]]
        
        EXAMPLE:
        Consider we have 40 particles. We then round it down to nearest cube, which is 27. Thus we create a meshgrid
        with side length 3. Now we start the process of assignment. Particle #1 is placed into cell {0, 0, 0}. 
        Particle #2 is placed into cell {1, 0, 0}; #3 - {2, 0, 0}; #4 - {0, 1, 0}; #5 - {1, 1, 0}; #6 - {2, 1, 0};
        #7 - {0, 2, 0}; ... ; #10 - {0, 0, 1}; ... ; #27 - {2, 2, 2}; #28 - {0, 0, 0}, #29 - {1, 0, 0}, etc.
        Notation of coordinates is {x, y, z}.
        """

        #assigning coordinates
        self.pos = np.zeros((self.partCount, 3))
        for i in range(self.partCount):
            temp = i % (self.cubicParts1 ** 3)
            self.pos[i, :] = np.array([dists[int(temp % self.cubicParts1)] + random.rand(1)[0] * (self.radius * 0.5),
                                       dists[int((temp % self.cubicParts2) // self.cubicParts1)] + random.rand(1)[0] * (self.radius * 0.5),
                                       dists[int(temp // self.cubicParts2)] + random.rand(1)[0] * (self.radius * 0.5)])
            self.partBelonging[temp, 6] = i

        """
        Creating random speed matrix where values are placed in as:
        [[V_x_1, V_y_1, V_z_1] - speeds of the first particle projected on x, y, z axes  
         [V_x_2, V_y_2, V_z_2] - speeds of the second particle projected on x, y, z axes
                  ...
         [V_x_n, V_y_n, V_z_n]] - speeds of the n-th particle projected on x, y, z axes
        """
        self.vel = random.uniform(-1, 1, (self.partCount, 3)) * self.velNormalized

    def SetGraphs(self):
        """
        Setting up graphs with initial histogram state included. Graphs are located in the same window.
        Precise size of a window was chosen as a minimum size at which particles positions on the graph can be seen.
        """

        boxLimits = np.array([0, self.sideLength])

        # creating graph windows
        self.figure = plt.figure(figsize=(10.4, 5.85))

        self.particleGraph = plt.subplot2grid((18, 32), (1, 1), rowspan=16, colspan=16, projection='3d')
        self.particleGraph.set_xlim3d(boxLimits)
        self.particleGraph.set_ylim3d(boxLimits)
        self.particleGraph.set_zlim3d(boxLimits)
        self.particleGraph.set_xlabel('X')
        self.particleGraph.set_ylabel('Y')
        self.particleGraph.set_zlabel('Z')

        self.distributionGraph = plt.subplot2grid((18, 32), (6, 23), rowspan=5, colspan=9)
        self.distributionGraph.set_xlabel('Speed')
        self.distributionGraph.set_ylabel('Frequency')

        # setting up initial histogram state
        self.vel_hist_data = np.zeros(self.partCount)
        for i in range(self.partCount):
            self.vel_hist_data[i] = (self.vel[i, 0] ** 2 + self.vel[i, 1] ** 2 + self.vel[i, 2] ** 2) ** (1 / 2)

    def Step(self, dt):
        """
        This module computes changes in system which happens after set period of time dt (aka steps).

        Collisions between particles are only calculated for particles inside cells, which where defined in previous
        module.

        To do that, each step we first check to which cell does each particle belong. To do that we simply do 3*n
        checks, where n - number of particles. After that we check collisions of particles inside of a cell.
        This method improves our calculations time because in a straightforward approach we make n^2 calculations
        (it is n*(n-1) to be exact but for big n in which we are interested we can say it is n^2) of
        distances between particles, and after that we make (n^2)/2 checks of collisions. In this modified approach
        we only make 3*n calculations of belongings, after that we make (n/m)^2 calculations of distances between
        particles, where m - number of cells. And lastly we make m * ((n/m)^2)/2 checks of collisions. Therefore we only
        do 3*n+(n/m)^2 calculations, which is less than n^2 by a lot in our situation. m * ((n/m)^2)/2 = (n^2)/2m, which
        is less than (n^2)/2.
        """

        # updating positions of the particles after dt period of time
        self.pos = self.pos + self.vel * dt

        """
        In this part we set up an array of cells and particles inside of them. Layout of an array is as follows:
        [[x_1_edge, x_2_edge, y_1_edge, y_2_edge, z_1_edge, z_2_edge, particle_index_1, particle_index_2, ... ]
         [x_1_edge, x_2_edge, y_1_edge, y_2_edge, z_1_edge, z_2_edge, particle_index_n, particle_index_n+1, ...]
                                                    .........
        ]
        where edges are edges of cells, x_1, x_2 - closer and farther edges of a cell (closer = closer to origin point
        (0, 0, 0)).
        If there is no vacant slot for a new particle, new column is created, vacant slots are marked as 0. 
        """

        # finding colliding particles, can be improved by creating a grid
        distances = squareform(pdist(self.pos))
        ind1, ind2 = np.where(distances < 2 * self.radius)
        unique = (ind1 < ind2)
        ind1 = ind1[unique]
        ind2 = ind2[unique]

        # calculating the result of the collision
        for i1, i2 in zip(ind1, ind2):
            vel_cm = (self.vel[i1] + self.vel[i2]) / 2
            vec_normal = self.pos[i1] - self.pos[i2]
            vel_normal = self.vel[i1] - self.vel[i2]
            vel_change = 2 * np.dot(vec_normal, vel_normal) * vec_normal / np.dot(vec_normal, vec_normal) - vel_normal
            self.vel[i1] = vel_cm - vel_change / 2
            self.vel[i2] = vel_cm + vel_change / 2
            self.pos[i1] += self.vel[i1] * dt
            self.pos[i2] += self.vel[i2] * dt

        # finding particles colliding with the wall and the change of momentum
        for i in range(self.partCount):
            if self.pos[i, [0]] - self.radius < 0:
                self.vel[i, [0]] = -self.vel[i, [0]]
                self.pos[i, [0]] = self.radius * 1.01
                """
                This is 
                """
                # # finding change of momentum
                # self.dp += 2 * abs(self.vel[i, [0]]) * self.mass_non_normed
                # self.counter += 1
            if self.pos[i, [0]] + self.radius > self.sideLength:
                self.vel[i, [0]] = -self.vel[i, [0]]
                self.pos[i, [0]] = self.sideLength - (self.radius * 1.01)
            if self.pos[i, [1]] - self.radius < 0:
                self.vel[i, [1]] = -self.vel[i, [1]]
                self.pos[i, [1]] = self.radius * 1.01
            if self.pos[i, [1]] + self.radius > self.sideLength:
                self.vel[i, [1]] = -self.vel[i, [1]]
                self.pos[i, [1]] = self.sideLength - (self.radius * 1.01)
            if self.pos[i, [2]] - self.radius < 0:
                self.vel[i, [2]] = -self.vel[i, [2]]
                self.pos[i, [2]] = self.radius * 1.01
            if self.pos[i, [2]] + self.radius > self.sideLength:
                self.vel[i, [2]] = -self.vel[i, [2]]
                self.pos[i, [2]] = self.sideLength - (self.radius * 1.01)

        # finding the pressure
        # self.pressure = self.dp / (self.counter * dt * (self.side_length ** 2))
        # print(self.pressure)
        # self.left_hand_side = self.pressure * (self.side_length ** 3 - self.b)
        # print(self.left_hand_side)
        # print(self.counter)
        # if self.counter > 3e3:
        #     self.dp = 0
        #     self.side_length *= 1.2
        #     self.counter = 0



def init():
    global abobus_3d
    molecules.set_data_3d([], [], [])
    ax2.set_xlim(0, 1.5)
    ax2.set_ylim(0, 2)
    return molecules,

def animate(a):
    global abobus_3d, dt, bars, data
    ax2.clear()
    ax2.set_xlim(0, 1.5)
    ax2.set_ylim(0, 2)
    abobus_3d.step(dt)
    molecules.set_data_3d(abobus_3d.pos[:, 0], abobus_3d.pos[:, 1], abobus_3d.pos[:, 2])
    molecules.set_markersize(1)
    for i in range(abobus_3d.partCount):
        data[i] = (abobus_3d.vel[i, 0] ** 2 + abobus_3d.vel[i, 1] ** 2 + abobus_3d.vel[i, 2] ** 2) ** (1 / 2)
    _, _, bars = ax2.hist(data, bins = 100, lw=1, density=True, alpha=0.75)
    ax2.plot(x, p)
    # plt.savefig(str(a) + ".png")
    return bars.patches + [molecules]

def my_dist(v, mass, temp):
    return ((2 / np.pi) ** (1/2)) * ((mass / (1.87e-23 * temp)) ** (3/2)) * \
           (v ** 2) * np.exp(-mass * (v ** 2) / (2 * 1.87e-23 * temp))


abobus_3d = GasSimulation3d()
x = np.linspace(0, 5, 100)
p = my_dist(x, abobus_3d.mass, 300)
dt = 1. / 500000000
fig = abobus_3d.figure
ax1 = abobus_3d.ax1
ax2 = abobus_3d.ax2
ax2.plot(x, p)
data = abobus_3d.vel_hist_data
_, _, bars = ax2.hist([], bins = 100, lw=1, density=True, alpha=0.75)
molecules, = ax1.plot([], [], [], 'p')
ani = animation.FuncAnimation(fig, animate, frames=300, interval=40, blit=True, init_func=init)
#ani.save('particle_box_3d_test.mp4', fps=30, extra_args=['-vcodec', 'libx264'])
plt.show()
