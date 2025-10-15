#!/usr/bin/env python3
"""Utility script to test each joint of a MoveIt group sequentially."""

import math
from typing import List

import rospy
from moveit_commander import MoveGroupCommander, RobotCommander, roscpp_initialize, roscpp_shutdown


class SequentialJointTester:
    """Move one joint at a time within its safe limits."""

    def __init__(self) -> None:
        roscpp_initialize([])
        rospy.init_node("sequential_joint_test", anonymous=True)

        self._group_name = rospy.get_param("~group", "right_arm")
        self._delta = rospy.get_param("~delta", 0.2)
        self._pause = rospy.get_param("~pause", 2.0)

        self._robot = RobotCommander()
        self._group = MoveGroupCommander(self._group_name)

        self._joint_names = self._group.get_active_joints()
        rospy.loginfo("Testing group '%s' with joints: %s", self._group_name, self._joint_names)

    def run(self) -> None:
        if not self._joint_names:
            rospy.logwarn("No active joints found for group '%s'", self._group_name)
            return

        start_positions = self._group.get_current_joint_values()
        rospy.loginfo("Starting positions: %s", start_positions)

        for index, joint_name in enumerate(self._joint_names):
            rospy.loginfo("Testing joint %s", joint_name)
            self._move_single_joint(index, joint_name, start_positions)

        rospy.loginfo("Returning to start positions")
        self._execute_joint_goal(start_positions)

    def _move_single_joint(self, index: int, joint_name: str, reference: List[float]) -> None:
        joint = self._robot.get_joint(joint_name)
        lower = joint.min_bound()
        upper = joint.max_bound()
        rospy.logdebug("Joint %s bounds: [%s, %s]", joint_name, lower, upper)

        if math.isinf(lower) or math.isinf(upper):
            rospy.logwarn("Joint %s does not have finite bounds, skipping", joint_name)
            return

        goal = list(reference)
        current = reference[index]
        offset = self._delta

        target = current + offset
        margin = 0.05
        target = min(target, upper - margin)
        target = max(target, lower + margin)

        if abs(target - current) < 1e-4:
            target = current - offset
            target = min(target, upper - margin)
            target = max(target, lower + margin)

        if abs(target - current) < 1e-4:
            rospy.logwarn("Joint %s cannot move within safe range, skipping", joint_name)
            return

        goal[index] = target
        rospy.loginfo("Moving joint %s to %.3f rad", joint_name, target)
        self._execute_joint_goal(goal)

        rospy.sleep(self._pause)

    def _execute_joint_goal(self, goal: List[float]) -> None:
        self._group.go(goal, wait=True)
        self._group.stop()


def main() -> None:
    tester = SequentialJointTester()
    try:
        tester.run()
    finally:
        roscpp_shutdown()


if __name__ == "__main__":
    main()
