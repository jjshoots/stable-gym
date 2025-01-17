"""The oscillator gymnasium environment."""
import gymnasium as gym
import matplotlib.pyplot as plt
import numpy as np
from gymnasium import logger, spaces

if __name__ == "__main__":
    from oscillator_disturber import OscillatorDisturber
else:
    from .oscillator_disturber import OscillatorDisturber

EPISODES = 10  # Number of env episodes to run when __main__ is called.
RANDOM_STEP = True  # Use random action in __main__. Zero action otherwise.


# TODO: Update solving criteria after training.
class Oscillator(gym.Env, OscillatorDisturber):
    """Synthetic oscillatory network environment.

    .. Note::
        Can also be used in a vectorized manner. See the
        :gymnasium:`gym.vector <api/vector>` documentation.

    .. note::
        This gymnasium environment inherits from the
        :class:`~stable_gym.common.disturber.Disturber`
        in order to be able to use it with the Robustness Evaluation tool of the
        Stable Learning Control package (SLC). For more information see
        `the SLC documentation <https://rickstaa.dev/stable-learning-control/utils/tester.html#robustness-eval-utility>`_.

    Description:
        The goal of the agent in the oscillator environment is to act in such a way that
        one of the proteins of the synthetic oscillatory network follows a supplied
        reference signal.

    Source:
        This environment corresponds to the Oscillator environment used in the paper
        `Han et al. 2020`_.

    .. _`Han et al. 2020`: https://arxiv.org/abs/2004.14288

    Observation:
        **Type**: Box(7) or Box(8) depending on the ``exclude_reference_error_from_observation`` argument.

        +-----+-----------------------------------------------+-------------------+-------------------+
        | Num | Observation                                   | Min               | Max               |
        +=====+===============================================+===================+===================+
        | 0   | Lacl mRNA transcripts concentration           | 0                 | 100               |
        +-----+-----------------------------------------------+-------------------+-------------------+
        | 1   | tetR mRNA transcripts concentration           | 0                 | 100               |
        +-----+-----------------------------------------------+-------------------+-------------------+
        | 2   | CI mRNA transcripts concentration             | 0                 | 100               |
        +-----+-----------------------------------------------+-------------------+-------------------+
        | 3   || lacI (repressor) protein concentration       | 0                 | 100               |
        |     || (Inhibits transcription of the tetR gene)    |                   |                   |
        +-----+-----------------------------------------------+-------------------+-------------------+
        | 4   || tetR (repressor) protein concentration       | 0                 | 100               |
        |     || (Inhibits transcription of CI gene)          |                   |                   |
        +-----+-----------------------------------------------+-------------------+-------------------+
        | 5   || CI (repressor) protein concentration         | 0                 | 100               |
        |     || (Inhibits transcription of lacI gene)        |                   |                   |
        +-----+-----------------------------------------------+-------------------+-------------------+
        | 6   | The reference we want to follow               | 0                 | 100               |
        +-----+-----------------------------------------------+-------------------+-------------------+
        | (7) || **Optional** - The error between the current | -100              | 100               |
        |     || value of protein 1 and the reference         |                   |                   |
        +-----+-----------------------------------------------+-------------------+-------------------+

    Actions:
        **Type**: Box(3)

        +-----+------------------------------------------------------------+---------+---------+
        | Num | Action                                                     | Min     |   Max   |
        +=====+============================================================+=========+=========+
        | 0   || Relative intensity of light signal that induce the        | -5      | 5       |
        |     || expression of the Lacl mRNA gene.                         |         |         |
        +-----+------------------------------------------------------------+---------+---------+
        | 1   || Relative intensity of light signal that induce the        | -5      | 5       |
        |     || expression of the tetR mRNA gene.                         |         |         |
        +-----+------------------------------------------------------------+---------+---------+
        | 2   || Relative intensity of light signal that induce the        | -5      | 5       |
        |     || expression of the CI mRNA gene.                           |         |         |
        +-----+------------------------------------------------------------+---------+---------+

    Cost:
        A cost, computed as the sum of the squared differences between the estimated and the actual states:

        .. math::

            C = {p_1 - r_1}^2

    Starting State:
        All observations are assigned a uniform random value in ``[0..5]``

    Episode Termination:
        -   An episode is terminated when the maximum step limit is reached.
        -   The step cost is greater than 100.

    Solved Requirements:
        Considered solved when the average cost is lower than 300.

    How to use:
        .. code-block:: python

            import stable_gym
            import gymnasium as gym
            env = gym.make("CartPoleCost-v1")

        On reset, the ``options`` parameter allows the user to change the bounds used to
        determine the new random state when ``random=True``.

    Attributes:
        state (numpy.ndarray): The current system state.
        t (float): The current time step.
        dt (float): The environment step size. Also available as :attr:`.tau`.
        sigma (float): The variance of the system noise.
    """  # noqa: E501

    instances = 0  # Number of instances created.

    def __init__(
        self,
        render_mode=None,
        reference_target_position=8.0,
        reference_amplitude=7.0,
        reference_frequency=(1 / 200),  # NOTE: Han et al. 2020 uses a period of 200.
        reference_phase_shift=0.0,
        clip_action=True,
        exclude_reference_from_observation=False,
        exclude_reference_error_from_observation=True,
    ):
        """Initialise a new Oscillator environment instance.

        Args:
            render_mode (str, optional): The render mode you want to use. Defaults to
                ``None``. Not used in this environment.
            reference_target_position: The reference target position, by default
                ``8.0`` (i.e. the mean of the reference signal).
            reference_amplitude: The reference amplitude, by default ``7.0``.
            reference_frequency: The reference frequency, by default ``0.005``.
            reference_phase_shift: The reference phase shift, by default ``0.0``.
            clip_action (str, optional): Whether the actions should be clipped if
                they are greater than the set action limit. Defaults to ``True``.
            exclude_reference_from_observation (bool, optional): Whether the reference
                should be excluded from the observation. Defaults to ``False``.
            exclude_reference_error_from_observation (bool, optional): Whether the error
                should be excluded from the observation. Defaults to ``True``.
        """
        super().__init__()  # Setup disturber.
        self._action_clip_warning = False
        self._clip_action = clip_action
        self._exclude_reference_from_observation = exclude_reference_from_observation
        self._exclude_reference_error_from_observation = (
            exclude_reference_error_from_observation
        )

        # Validate input arguments.
        assert (reference_amplitude == 0 or reference_frequency == 0) or not (
            exclude_reference_from_observation
            and exclude_reference_error_from_observation
        ), (
            "The agent needs to observe either the reference or the reference error "
            "for it to be able to learn when the reference is not constant."
        )
        assert (
            reference_frequency >= 0
        ), "The reference frequency must be greater than or equal to zero."

        self.t = 0.0
        self.dt = 1.0
        self._init_state = np.array(
            [0.8, 1.5, 0.5, 3.3, 3, 3]
        )  # Used when random is disabled in reset.
        self._init_state_range = {
            "low": [0, 0, 0, 0, 0, 0],
            "high": [5, 5, 5, 5, 5, 5],
        }  # Used when random is enabled in reset.

        # Set oscillator network parameters.
        self.K1 = 1.0  # mRNA dissociation constants m1.
        self.K2 = 1.0  # mRNA dissociation constant m2.
        self.K3 = 1.0  # mRNA dissociation constant m3.
        self.a1 = 1.6  # Maximum promoter strength m1.
        self.a2 = 1.6  # Maximum promoter strength m2.
        self.a3 = 1.6  # Maximum promoter strength m3.
        self.gamma1 = 0.16  # mRNA degradation rate m1.
        self.gamma2 = 0.16  # mRNA degradation rate m2.
        self.gamma3 = 0.16  # mRNA degradation rate m3.
        self.beta1 = 0.16  # Protein production rate p1.
        self.beta2 = 0.16  # Protein production rate p2.
        self.beta3 = 0.16  # Protein production rate p3.
        self.c1 = 0.06  # Protein degradation rate p1.
        self.c2 = 0.06  # Protein degradation rate p2.
        self.c3 = 0.06  # Protein degradation rate p3.
        self.b1 = 1.0  # Control input gain u1.
        self.b2 = 1.0  # Control input gain u2.
        self.b3 = 1.0  # Control input gain u3.

        # Set noise parameters.
        # NOTE: Zero during training.
        self.delta1 = 0.0  # m1 noise.
        self.delta2 = 0.0  # m2 noise.
        self.delta3 = 0.0  # m3 noise.
        self.delta4 = 0.0  # p1 noise.
        self.delta5 = 0.0  # p2 noise.
        self.delta6 = 0.0  # p3 noise.

        obs_low = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        obs_high = np.array([100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
        if not self._exclude_reference_from_observation:
            obs_low = np.append(obs_low, 0.0)
            obs_high = np.append(obs_high, 100.0)
        if not self._exclude_reference_error_from_observation:
            obs_low = np.append(obs_low, -100.0)
            obs_high = np.append(obs_high, 100.0)
        self.action_space = spaces.Box(
            low=np.array([-5.0, -5.0, -5.0]),
            high=np.array([5.0, 5.0, 5.0]),
            dtype=np.float64,
        )
        self.observation_space = spaces.Box(obs_low, obs_high, dtype=np.float64)
        self.reward_range = (0.0, 100.0)

        self.viewer = None
        self.state = None
        self.steps_beyond_done = None

        # Reference target, amplitude, frequency and phase shift.
        self.reference_target_pos = reference_target_position
        self.reference_amplitude = reference_amplitude
        self.reference_frequency = reference_frequency
        self.phase_shift = reference_phase_shift

        # Print vectorization debug info.
        self.__class__.instances += 1
        self.instance_id = self.__class__.instances
        logger.debug(f"Oscillator instance '{self.instance_id}' created.")

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
        if self._clip_action:
            # Throw warning if clipped and not already thrown.
            if not self.action_space.contains(action) and not self._action_clip_warning:
                logger.warn(
                    f"Action '{action}' was clipped as it is not in the action_space "
                    f"'high: {self.action_space.high}, low: {self.action_space.low}'."
                )
                self._action_clip_warning = True

            u1, u2, u3 = np.clip(action, self.action_space.low, self.action_space.high)
        else:
            assert self.action_space.contains(
                action
            ), f"{action!r} ({type(action)}) invalid"
            u1, u2, u3 = action
        assert self.state is not None, "Call reset before using step method."

        # Perform action in the environment and return the new state.
        # NOTE: The new state is found by solving 3 first-order differential equations.
        m1, m2, m3, p1, p2, p3 = self.state  # NOTE: [x1, x2, x3, x4, x5, x6] in paper.
        m1_dot = -self.gamma1 * m1 + self.a1 / (self.K1 + np.square(p3)) + self.b1 * u1
        m2_dot = -self.gamma2 * m2 + self.a2 / (self.K2 + np.square(p1)) + self.b2 * u2
        m3_dot = -self.gamma3 * m3 + self.a3 / (self.K3 + np.square(p2)) + self.b3 * u3
        p1_dot = -self.c1 * p1 + self.beta1 * m1
        p2_dot = -self.c2 * p2 + self.beta2 * m2
        p3_dot = -self.c3 * p3 + self.beta3 * m3

        # Calculate mRNA concentrations.
        # Note: Use max to make sure concentrations can not be negative.
        m1 = np.max(
            [
                m1
                + m1_dot * self.dt
                + self.np_random.uniform(-self.delta1, self.delta1, 1),
                np.zeros([1]),
            ]
        )
        m2 = np.max(
            [
                m2
                + m2_dot * self.dt
                + self.np_random.uniform(-self.delta2, self.delta2, 1),
                np.zeros([1]),
            ]
        )
        m3 = np.max(
            [
                m3
                + m3_dot * self.dt
                + self.np_random.uniform(-self.delta3, self.delta3, 1),
                np.zeros([1]),
            ]
        )

        # Calculate protein concentrations.
        # Note: Use max to make sure concentrations can not be negative.
        p1 = np.max(
            [
                p1
                + p1_dot * self.dt
                + self.np_random.uniform(-self.delta4, self.delta4, 1),
                np.zeros([1]),
            ]
        )
        p2 = np.max(
            [
                p2
                + p2_dot * self.dt
                + self.np_random.uniform(-self.delta5, self.delta5, 1),
                np.zeros([1]),
            ]
        )
        p3 = np.max(
            [
                p3
                + p3_dot * self.dt
                + self.np_random.uniform(-self.delta6, self.delta6, 1),
                np.zeros([1]),
            ]
        )

        # Retrieve state.
        self.state = np.array([m1, m2, m3, p1, p2, p3])
        self.t = self.t + self.dt

        # Calculate cost.
        r1 = self.reference(self.t)
        cost = np.square(p1 - r1)

        # Define stopping criteria.
        terminated = cost < self.reward_range[0] or cost > self.reward_range[1]

        # Create observation and info_dict.
        obs = np.array([m1, m2, m3, p1, p2, p3])
        if not self._exclude_reference_from_observation:
            obs = np.append(obs, r1)
        if not self._exclude_reference_error_from_observation:
            obs = np.append(obs, p1 - r1)
        info_dict = dict(
            reference=r1,
            state_of_interest=p1,
            reference_error=p1 - r1,
        )

        # Return state, cost, terminated, truncated and info_dict.
        return (
            obs,
            cost,
            terminated,
            False,
            info_dict,
        )

    def reset(
        self,
        seed=None,
        options=None,
        random=True,
    ):
        """Reset gymnasium environment.

        Args:
            seed (int, optional): A random seed for the environment. By default
                ``None``.
            options (dict, optional): A dictionary containing additional options for
                resetting the environment. By default ``None``. Not used in this
                environment.
            random (bool, optional): Whether we want to randomly initialise the
                environment. By default True.

        Returns:
            (tuple): tuple containing:

                -   obs (:obj:`numpy.ndarray`): Initial environment observation.
                -   info (:obj:`dict`): Dictionary containing additional information.
        """
        super().reset(seed=seed)

        # Initialise custom bounds while ensuring that the bounds are valid.
        # NOTE: If you use custom reset bounds, it may lead to out-of-bound
        # state/observations.
        low = np.array(
            options["low"]
            if options is not None and "low" in options
            else self._init_state_range["low"]
        )
        high = np.array(
            options["high"]
            if options is not None and "high" in options
            else self._init_state_range["high"]
        )
        assert (
            self.observation_space.contains(
                np.append(
                    low,
                    np.zeros(self.observation_space.shape[0] - low.shape[0]),
                )
            )
        ) and (
            self.observation_space.contains(
                np.append(
                    high,
                    np.zeros(self.observation_space.shape[0] - high.shape[0]),
                )
            )
        ), (
            "Reset bounds must be within the observation space bounds "
            f"({self.observation_space})."
        )

        # Set initial state, reset time, retrieve initial observation and info_dict.
        self.state = (
            self.np_random.uniform(low=low, high=high, size=(6,))
            if random
            else self._init_state
        )
        self.t = 0.0
        m1, m2, m3, p1, p2, p3 = self.state
        r1 = self.reference(self.t)
        obs = np.array([m1, m2, m3, p1, p2, p3])
        if not self._exclude_reference_from_observation:
            obs = np.append(obs, r1)
        if not self._exclude_reference_error_from_observation:
            obs = np.append(obs, p1 - r1)
        info_dict = dict(
            reference=r1,
            state_of_interest=p1,
            reference_error=p1 - r1,
        )

        # Return initial observation and info_dict.
        return obs, info_dict

    def reference(self, t):
        r"""Returns the current value of the periodic reference signal that is tracked by
        the Synthetic oscillatory network.

        Args:
            t (float): The current time step.

        Returns:
            float: The current reference value.

        .. note::

            This uses the general form of a periodic signal:

            .. math::

                y(t) = A \sin(\omega t + \phi) + C \\
                y(t) = A \sin(2 \pi f t + \phi) + C \\
                y(t) = A \sin(\frac{2 \pi}{T} t + \phi) + C

            Where:

            -   :math:`t` is the time.
            -   :math:`A` is the amplitude of the signal.
            -   :math:`\omega` is the frequency of the signal.
            -   :math:`f` is the frequency of the signal.
            -   :math:`T` is the period of the signal.
            -   :math:`\phi` is the phase of the signal.
            -   :math:`C` is the offset of the signal.
        """
        return self.reference_target_pos + self.reference_amplitude * np.sin(
            ((2 * np.pi) * self.reference_frequency * t) - self.phase_shift
        )

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
            "No render method was implemented yet for the Oscillator environment."
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
    print("Setting up 'Oscillator' environment.")
    env = gym.make("Oscillator")

    # Run episodes.
    episode = 0
    path, paths = [], []
    reference, references = [], []
    s, info = env.reset()
    path.append(s)
    reference.append(info["reference"])
    print(f"\nPerforming '{EPISODES}' in the 'Oscillator' environment...\n")
    print(f"Episode: {episode}")
    while episode <= EPISODES:
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
    print("\nFinished 'Oscillator' environment simulation.")

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
        ax.set_title(f"Oscillator episode '{i+1}'")

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
