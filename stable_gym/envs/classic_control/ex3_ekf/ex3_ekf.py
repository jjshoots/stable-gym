"""The noisy master slave system (Ex3EKF) gymnasium environment."""
import gymnasium as gym
import matplotlib.pyplot as plt
import numpy as np
from gymnasium import logger, spaces

if __name__ == "__main__":
    from ex3_ekf_disturber import Ex3EKFDisturber
else:
    from .ex3_ekf_disturber import Ex3EKFDisturber

EPISODES = 10  # Number of env episodes to run when __main__ is called.
RANDOM_STEP = True  # Use random action in __main__. Zero action otherwise.


class Ex3EKF(gym.Env, Ex3EKFDisturber):
    """Noisy master slave system

    .. note::
        This gymnasium environment inherits from the
        :class:`~stable_gym.common.disturber.Disturber`
        in order to be able to use it with the Robustness Evaluation tool of the
        Stable Learning Control package (SLC). For more information see
        `the SLC documentation <https://rickstaa.dev/stable-learning-control/utils/tester.html#robustness-eval-utility>`_.

    Description:
        The goal of the agent in the Ex3EKF environment is to act in such a way that
        estimator perfectly estimated the original noisy system. By doing this it serves
        as a RL based stationary Kalman filter.

    Observation:
        **Type**: Box(4)

        +-----+------------------------+----------------------+--------------------+
        | Num | Observation            | Min                  | Max                |
        +=====+========================+======================+====================+
        | 0   | The estimated angle    | -10000 rad           | 10000 rad          |
        +-----+------------------------+----------------------+--------------------+
        | 1   | The estimated frequency| -10000 hz            | 10000 hz           |
        +-----+------------------------+----------------------+--------------------+
        | 2   | Actual angle           | -10000 rad           | 10000 rad          |
        +-----+------------------------+----------------------+--------------------+
        | 3   | Actual frequency       | -10000 rad           | 10000 rad          |
        +-----+------------------------+----------------------+--------------------+

    Actions:
        **Type**: Box(2)

        +-----+-----------------------------------------------+
        | Num | Action                                        |
        +=====+===============================================+
        | 0   | First action coming from the RL Kalman filter |
        +-----+-----------------------------------------------+
        | 1   | Second action coming from the RL Kalman filter|
        +-----+-----------------------------------------------+

    Cost:
        A cost, computed as the sum of the squared differences between the estimated and the actual states:

        .. math::

            C = {(\\hat{x}_1 - x_1)}^2 + {(\\hat{x}_2 - x_2)}^2

    Starting State:
        All observations are assigned a uniform random value in ``[-0.05..0.05]``

    Episode Termination:
        -   When the step cost is higher than 100.

    Solved Requirements:
        Considered solved when the average cost is lower than 300.

    Attributes:
        state (numpy.ndarray): The current system state.
        t (float): The current time step.
        dt (float): The environment step size. Also available as :attr:`.tau`.
        sigma (float): The variance of the system noise.
    """  # noqa: E501

    def __init__(
        self,
        render_mode=None,
        clipped_action=True,
    ):
        """Initialise new Ex3EKF environment instance.

        Args:
            render_mode (str, optional): The render mode you want to use. Defaults to
                ``None``. Not used in this environment.
            clipped_action (str, optional): Whether the actions should be clipped if
                they are greater than the set action limit. Defaults to ``True``.
        """
        if render_mode is not None:
            logger.warn(
                "You are passing the `render_mode` argument to the `__init__` method "
                "of the Ex3EKF environment. This argument is not used in this "
                "environment."
            )

        super().__init__()  # Setup disturber.
        self._action_clip_warning = False

        self.t = 0.0
        self.dt = 0.1

        # Setup Ex3EKF parameters
        self.q1 = 0.01
        self.g = 9.81
        self.l_net = 1.0
        self.mean1 = [0, 0]
        self.cov1 = np.array(
            [
                [1 / 3 * (self.dt) ** 3 * self.q1, 1 / 2 * (self.dt) ** 2 * self.q1],
                [1 / 2 * (self.dt) ** 2 * self.q1, self.dt * self.q1],
            ]
        )
        self.mean2 = 0
        self.cov2 = 1e-2
        self.missing_rate = 0
        self.sigma = 0

        # Displacement limit set to be [-high, high]
        high = np.array([10000, 10000, 10000, 10000], dtype=np.float32)

        self.action_space = spaces.Box(
            low=np.array([-10.0, -10.0], dtype=np.float32),
            high=np.array([10.0, 10.0], dtype=np.float32),
            dtype=np.float32,
        )
        self.observation_space = spaces.Box(-high, high, dtype=np.float32)
        self.reward_range = (0.0, 100.0)

        self._clipped_action = clipped_action
        self.viewer = None
        self.state = None
        self.output = None
        self.steps_beyond_done = None

    def step(self, action):
        """Take step into the environment.

        Args:
            action (numpy.ndarray): The action we want to perform in the environment.

        Returns:
            (tuple): tuple containing:

                -   obs (:obj:`np.ndarray`): Environment observation.
                -   cost (:obj:`float`): Cost of the action.
                -   terminated (:obj:`bool`): Whether the episode is terminated.
                -   truncated (:obj:`bool`): Whether the episode was truncated. This
                    value is set by wrappers when for example a time limit is reached or
                    the agent goes out of bounds.
                -   info (:obj:`dict`): Additional information about the environment.
        """
        # Clip action if needed.
        if self._clipped_action:
            if (
                (action < self.action_space.low).any()
                or (action > self.action_space.high).any()
                and not self._action_clip_warning
            ):
                logger.warn(
                    f"Action '{action}' was clipped as it is not in the action_space "
                    f"'high: {self.action_space.high}, low: {self.action_space.low}'."
                )
                self._action_clip_warning = True
            u1, u2 = np.clip(action, self.action_space.low, self.action_space.high)
        else:
            u1, u2 = action

        # Perform action in the environment and return the new state.
        t = self.t
        input = 0 * np.cos(t) * self.dt

        # Retrieve slave state.
        hat_x_1, hat_x_2, x_1, x_2 = self.state

        # Retrieve master state.
        x_1 = x_1 + self.dt * x_2
        x_2 = x_2 - self.g * self.l_net * np.sin(x_1) * self.dt + input
        state = np.array([x_1, x_2])
        state = (
            state + self.np_random.multivariate_normal(self.mean1, self.cov1).flatten()
        )  # Add process noise.
        x_1, x_2 = state

        # Retrieve reference.
        y_1 = self.reference(x_1)
        hat_y_1 = np.sin(hat_x_1 + self.dt * hat_x_2)

        # Mimic the signal drop rate.
        # flag=1: received
        # flag=0: dropout
        (flag) = self.np_random.binomial(1, 1 - self.missing_rate, 1)
        if flag == 1:
            hat_x_1 = hat_x_1 + self.dt * hat_x_2 + self.dt * u1 * (y_1 - hat_y_1)
            hat_x_2 = (
                hat_x_2
                - self.g * np.sin(hat_x_1) * self.dt
                + self.dt * u2 * (y_1 - hat_y_1)
                + input
            )
        else:
            hat_x_1 = hat_x_1 + self.dt * hat_x_2
            hat_x_2 = hat_x_2 - self.g * np.sin(hat_x_1) * self.dt + input

        # Calculate cost.
        cost = np.square(hat_x_1 - x_1) + np.square(hat_x_2 - x_2)
        # cost = np.abs(hat_x_1 - x_1)**1 + np.abs(hat_x_2 - x_2)**1

        # Define stopping criteria.
        terminated = cost < self.reward_range[0] or cost > self.reward_range[1]

        # Update state.
        self.state = np.array([hat_x_1, hat_x_2, x_1, x_2])
        self.output = y_1
        self.t = self.t + self.dt

        # Return state, cost, terminated, truncated and info_dict
        return (
            np.array([hat_x_1, hat_x_2, x_1, x_2]),
            cost,
            terminated,
            False,
            dict(
                reference=y_1,
                state_of_interest=np.array([hat_x_1 - x_1, hat_x_2 - x_2]),
            ),
        )

    def reset(self, seed=None, options=None):
        """Reset gymnasium environment.

        Args:
            seed (int, optional): A random seed for the environment. By default
                `None``.
            options (dict, optional): A dictionary containing additional options for
                resetting the environment. By default ``None``. Not used in this
                environment.

        Returns:
            (tuple): tuple containing:

                -   obs (:obj:`numpy.ndarray`): Initial environment observation.
                -   info (:obj:`dict`): Dictionary containing additional information.
        """
        if options is not None:
            logger.warn(
                "You are passing the `options` argument to the `reset` method of the "
                "Ex3-EKF environment. This argument is not used in this "
                "environment."
            )

        super().reset(seed=seed)

        x_1 = self.np_random.uniform(-np.pi / 2, np.pi / 2)
        x_2 = self.np_random.uniform(-np.pi / 2, np.pi / 2)
        hat_x_1 = x_1 + self.np_random.uniform(-np.pi / 4, np.pi / 4)
        hat_x_2 = x_2 + self.np_random.uniform(-np.pi / 4, np.pi / 4)
        self.state = np.array([hat_x_1, hat_x_2, x_1, x_2])

        # Retrieve reference.
        y_1 = self.reference(x_1)

        self.output = y_1
        self.t = 0.0
        return np.array([hat_x_1, hat_x_2, x_1, x_2]), dict(
            reference=y_1,
            state_of_interest=np.array([hat_x_1 - x_1, hat_x_2 - x_2]),
        )

    def reference(self, x):
        """Returns the current value of the periodic reference signal that is tracked by
        the Synthetic oscillatory network.

        Args:
            x (float): The reference value.

        Returns:
            float: The current reference value.
        """
        return np.sin(x) + self.np_random.normal(self.mean2, np.sqrt(self.cov2))

    def render(self, mode="human"):
        """Render one frame of the environment.

        Args:
            mode (str, optional): Gym rendering mode. The default mode will do something
                human friendly, such as pop up a window.

        Raises:
            NotImplementedError: Will throw a NotImplimented error since the render
                method has not yet been implemented.

        Note:
            This currently is not yet implemented.
        """
        raise NotImplementedError(
            "No render method was implemented yet for the Ex3EKF environment."
        )

    @property
    def tau(self):
        """Alias for the environment step size. Done for compatibility with the
        other gymnasium environments.
        """
        return self.dt

    @property
    def physics_time(self):
        """Returns the physics time. Alias for :attr:`.t`."""
        return self.t


if __name__ == "__main__":
    print("Setting up 'Ex3EKF' environment.")
    env = gym.make("Ex3EKF")

    # Run episodes.
    episode = 0
    path, paths = [], []
    reference, references = [], []
    s, info = env.reset()
    path.append(s)
    reference.append(info["reference"])
    print(f"\nPerforming '{EPISODES}' in the 'Ex3EKF' environment...\n")
    print(f"Episode: {episode}")
    while episode + 1 <= EPISODES:
        action = (
            env.action_space.sample()
            if RANDOM_STEP
            else np.zeros(env.action_space.shape)
        )
        s, r, terminated, truncated, info = env.step(action)
        path.append(s)
        reference.append(info["reference"])
        if terminated or truncated:
            paths.append(path)
            references.append(reference)
            episode += 1
            path, reference = [], []
            s, info = env.reset()
            path.append(s)
            reference.append(info["reference"])
            print(f"Episode: {episode}")
    print("\nFinished 'Ex3EKF' environment simulation.")

    # Plot results per episode.
    print("\nPlotting episode data...")
    for i in range(len(paths)):
        path = paths[i]
        fig, ax = plt.subplots()
        print(f"\nEpisode: {i+1}")
        path = np.array(path)
        t = np.linspace(0, path.shape[0] * env.dt, path.shape[0])
        for j in range(path.shape[1]):  # NOTE: Change if you want to plot less states.
            ax.plot(t, path[:, j], label=f"State {j+1}")
        ax.set_xlabel("Time (s)")
        ax.set_title(f"Ex3EKF episode '{i+1}'")

        # Plot reference signal.
        ax.plot(
            t,
            np.array(references[i]),
            color="black",
            linestyle="--",
            label="Reference",
        )
        ax.legend()
        print("Close plot to see next episode...")
        plt.show()

    print("\nDone")
