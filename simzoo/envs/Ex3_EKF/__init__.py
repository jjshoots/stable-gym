import sys

# Check if used as name_space package
if "simzoo" in sys.modules:
    from simzoo.envs.Ex3_EKF.Ex3_EKF import Ex3_EKF
    from simzoo.envs.Ex3_EKF.Ex3_EKF_negative import Ex3_EKF_negative
else:
    from machine_learning_control.simzoo.simzoo.envs.Ex3_EKF.Ex3_EKF import Ex3_EKF
    from machine_learning_control.simzoo.simzoo.envs.Ex3_EKF.Ex3_EKF_negative import (
        Ex3_EKF_negative,
    )
