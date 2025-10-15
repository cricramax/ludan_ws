#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rospy
from sensor_msgs.msg import JointState

def left_leg_callback(msg):
    rospy.loginfo("----- /mcu_leftleg/joint_states -----")
    print(msg)

def right_leg_callback(msg):
    rospy.loginfo("----- /mcu_rightleg/joint_states -----")
    print(msg)

def main():
    rospy.init_node('joint_states_echo', anonymous=True)

    rospy.Subscriber('/mcu_leftleg/joint_states', JointState, left_leg_callback)
    rospy.Subscriber('/mcu_rightleg/joint_states', JointState, right_leg_callback)

    rospy.loginfo("Listening to /mcu_leftleg/joint_states and /mcu_rightleg/joint_states ...")

    rospy.spin()

if __name__ == '__main__':
    main()
