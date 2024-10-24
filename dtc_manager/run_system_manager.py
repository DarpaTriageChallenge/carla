#!/usr/bin/env python

import os
import argparse
import yaml
import logging
import carla
import rclpy
import threading
import numpy as np
from rclpy.node import Node
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool
from std_msgs.msg import Empty
from std_msgs.msg import String
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Imu
from sensor_msgs.msg import NavSatFix
import time

python_file_path = os.path.realpath(__file__)
python_file_path = python_file_path.replace('run_system_manager.py', '')
global_transform = carla.Transform(carla.Location(x=0, y=0, z=0), carla.Rotation(yaw=180))


def get_quaternion_from_euler(roll, pitch, yaw):
    """
    Online Available rpy to quat conversion
    Convert an Euler angle to a quaternion.

    Input
    :param roll: The roll (rotation around x-axis) angle in radians.
    :param pitch: The pitch (rotation around y-axis) angle in radians.
    :param yaw: The yaw (rotation around z-axis) angle in radians.

    Output
    :return qx, qy, qz, qw: The orientation in quaternion [x,y,z,w] format
    """
    qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
    qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
    qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)

    return [qx, qy, qz, qw]

class SimulationStatusNode(Node):

    def __init__(self):
        super().__init__("carla_simulation_status")
        self._status = False
        self.publisher = self.create_publisher(Bool, "/simulation_ready", 10)
        self._timer = self.create_timer(0.1, self.publish_status)

    def publish_status(self):
        msg = Bool()
        msg.data = self._status
        self.publisher.publish(msg)
    
    def set_status(self, status):
        self._status = status

class SimulationStartNode(Node):

    def __init__(self):
        super().__init__("carla_simulation_start")
        self._start = False
        self._start_time = None
        self._timeout = 1800000000000 # 30 minutes in nanoseconds
        self.subscriber = self.create_subscription(Empty, "/simulation_start", self.set_start, 10)
    
    def get_start(self):
        return self._start
    
    def check_timeout(self):
        if self._start_time is None:
            return False

        if self.get_clock().now().nanoseconds - self._start_time >= self._timeout:
            return True
        return False

    def set_start(self, msg):
        self._start = True
        if self._start_time is None:
            self._start_time = self.get_clock().now().nanoseconds
            logging.info("  Start Time: %s", self._start_time)

class SimulationAudioNode(Node):

    def __init__(self):
        super().__init__("carla_audio_system")
        self.publisher = self.create_publisher(String, "/current_audio_file", 10)
        self._audio_file_name = "None"
        self._timer = self.create_timer(0.1, self.publish_audio)

    def publish_audio(self):
        msg = String()
        msg.data = self._audio_file_name
        self.publisher.publish(msg)
    
    def set_audio(self, file_name):
        self._audio_file_name = file_name

class SimulationGNSSNode(Node):

    def __init__(self):
        super().__init__("carla_simulation_gnss_tracker")
        self._current_imu_message = None
        self._current_gnss_message = None
        self._last_imu_message = None
        self._last_gnss_message = None
        self._has_moved = False
        self._is_stationary = False
        self._new_gnss_msg = False
        self._new_imu_msg = False
        self._should_track = False
        self._current_waypoint = 0
        self._time_at_waypoint = 0
        self._gps_eps = 0.0000001
        self._gps_alt_eps = 0.001
        self._imu_eps = 0.001
        self._is_at_waypoint_not_moving = False
        self._last_gnss_header_checked = None
        self.subscriber = self.create_subscription(Imu,       "/carla/dtc_vehicle/imu",  self.set_imu,       10)
        self.subscriber = self.create_subscription(NavSatFix, "/carla/dtc_vehicle/gnss", self.set_gnss,      10)
        self.subscriber = self.create_subscription(Clock,     "/clock",                  self.is_stationary, 10)
    
    def is_stationary(self, msg):
        # Check that we should be tracking stationary movement
        if not self._should_track:
            return False

        # Check that there are actually new messages and this information will not be checked multiple times
        if self._new_gnss_msg and self._new_imu_msg:
            # Reset so that we are waiting for new messages again
            self._new_gnss_msg = False
            self._new_imu_msg = False

        # Will check if the previous and current IMU messages are identical.
        # When Linear Accel and Angular Vel differentials are both 0,
        # The vehicle is assumed to be stationary
        if self._current_imu_message is None or self._last_imu_message is None:
            return False
        
        # Will also check if previous and current GPS signals are identical
        # When the lat/long/alt do not change, we are stationary, thus at a waypoint
        # Then this will check if it should tick up the current waypoint we are at
        if self._current_gnss_message is None or self._last_gnss_message is None:
            return False

        # Assume stationary and set to False if movement detected in any direction
        # this is done on a per axis basis but could be made better is linear math used
        self._is_stationary = True
        if abs(self._last_imu_message.angular_velocity.x - self._current_imu_message.angular_velocity.x) > self._imu_eps:
            self._is_stationary = False
        if abs(self._last_imu_message.angular_velocity.y - self._current_imu_message.angular_velocity.y) > self._imu_eps:
            self._is_stationary = False
        if abs(self._last_imu_message.angular_velocity.z - self._current_imu_message.angular_velocity.z) > self._imu_eps:
            self._is_stationary = False

        # Assume at a waypoint and set to False if movement detected in any direction
        is_at_waypoint = True
        if abs(self._last_gnss_message.latitude - self._current_gnss_message.latitude) > self._gps_eps:
            is_at_waypoint = False
            self._is_stationary = False
        if abs(self._last_gnss_message.longitude - self._current_gnss_message.longitude) > self._gps_eps:
            is_at_waypoint = False
            self._is_stationary = False
        if abs(self._last_gnss_message.altitude - self._current_gnss_message.altitude) > self._gps_alt_eps:
            is_at_waypoint = False
            self._is_stationary = False

        # Check if the vehicle has moved at all. We want this to only trigger at the end, the sim starts with the vehicle
        # stationary. So return False until the vehicle has moved.
        if not self._has_moved:
            if not self._is_stationary:
                self._has_moved = True
            return False

        # If we are at a waypoint, we should tick up the current waypoint, only if we have not already done so
        # This is checked as we must move to the next waypoint, so we need to also check 
        # against the last state and how long we have been there, exactly 0.5 second at 20hz.
        if is_at_waypoint and not self._is_at_waypoint_not_moving and self._time_at_waypoint == 10:
            self._current_waypoint+=1
            self._is_at_waypoint_not_moving = True    
        elif is_at_waypoint:
            self._time_at_waypoint+=1
        elif not is_at_waypoint:
            self._is_at_waypoint_not_moving = False
            self._time_at_waypoint=0
    
    def get_is_stationary(self):
        return self._is_stationary

    def get_current_waypoint(self):
        return self._current_waypoint
    
    def start_tracking(self):
        self._should_track = True

    def set_imu(self, msg):
        if self._current_imu_message is not None:
            self._last_imu_message = self._current_imu_message
        self._current_imu_message = msg
        self._new_imu_msg = True

    def set_gnss(self, msg):
        if self._current_gnss_message is not None:
            self._last_gnss_message = self._current_gnss_message
        self._current_gnss_message = msg
        self._new_gnss_msg = True

class SimulationVehicleOdometryNode(Node):

    def __init__(self):
        super().__init__("carla_vehicle_odometry_node")
        self._vehicle = None
        self._simulation_started = False
        self.publisher = self.create_publisher(Odometry, "/carla/dtc_vehicle/odometry", 10)
        self._timer = self.create_timer(0.1, self.publish_odom)

    def publish_odom(self):
        if self._vehicle is None or self._simulation_started == False:
            return

        msg = Odometry()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'dtc_vehicle'
        msg.child_frame_id = 'dtc_vehicle'

        transform = self._vehicle.get_transform()

        # Pose Y needs to be flipped
        msg.pose.pose.position.x = transform.location.x
        msg.pose.pose.position.y = -transform.location.y
        msg.pose.pose.position.z = transform.location.z

        # RPY comes in degrees, convert to rads, pitch and yaw needs to be converted to right hand rule
        roll = transform.rotation.roll * 0.0174533
        pitch = -transform.rotation.pitch * 0.0174533
        yaw = -transform.rotation.yaw * 0.0174533
        quat = get_quaternion_from_euler(roll, pitch, yaw)
        # returned [qx, qy, qz, qw]
        msg.pose.pose.orientation.x = quat[0]
        msg.pose.pose.orientation.y = quat[1]
        msg.pose.pose.orientation.z = quat[2]
        msg.pose.pose.orientation.w = quat[3]

        # NOTE TO ANYONE READING, Twist Used because the current system doesn't use physics

        self.publisher.publish(msg)
    
    def set_vehicle(self, vehicle):
        self._vehicle = vehicle

    def set_start(self):
        self._simulation_started = True

def _setup_waypoint_actors(world, scenario_file, bp_library):
    if 'waypoints' not in scenario_file:
        logging.info("  No Waypoints defined in Scenario File")
        raise Exception("No Waypoints defined in Scenario File")
    logging.info("  Setting Waypoints...")
    functor_sent_waypoints_bp = bp_library.filter("functorsendwaypoints")[0]
    iteration = 1
    last_zone = 0
    for waypoint_name in scenario_file['waypoints']:
        waypoint = scenario_file['waypoints'][waypoint_name]
        if 'zone' not in waypoint:
            logging.info("  No Zone defined in Waypoint Scenario Loadout")
            raise Exception("No Zone defined in Waypoint Scenario Loadout")
        # Set Casualty in Attribute
        if last_zone == waypoint['zone']:
            logging.info("  Zone defined twice in a row, must move to difference zones")
            raise Exception("Zone defined twice in a row, must move to difference zones")
        functor_sent_waypoints_bp.set_attribute(str(iteration), str(waypoint['zone']))
        iteration+=1
        last_zone = waypoint['zone']
    return world.spawn_actor(functor_sent_waypoints_bp, global_transform)

def _setup_dwell_time_actors(world, scenario_file, bp_library):
    if 'waypoints' not in scenario_file:
        logging.info("  No Waypoints defined in Scenario File")
        raise Exception("No Waypoints defined in Scenario File")
    logging.info("  Setting Waypoints...")
    functor_send_dwell_times_bp = bp_library.filter("functorsenddwelltimes")[0]
    iteration = 1
    for waypoint_name in scenario_file['waypoints']:
        waypoint = scenario_file['waypoints'][waypoint_name]
        if 'dwell_time' not in waypoint:
            logging.info("  No Dwell Time defined in Waypoint Scenario Loadout")
            raise Exception("No Dwell Time defined in Waypoint Scenario Loadout")
        # Set Casualty in Attribute
        functor_send_dwell_times_bp.set_attribute(str(iteration), str(waypoint['dwell_time']))
        iteration+=1
    return world.spawn_actor(functor_send_dwell_times_bp, global_transform)

def _setup_casualty_actors(world, scenario_file, bp_library):
    if 'casualties' not in scenario_file:
        logging.info("  No Casualties defined in Scenario File")
        raise Exception("No Casualties defined in Scenario File")
    logging.info("  Setting Casualties...")
    functor_sent_casualties_bp = bp_library.filter("functorsendcasualties")[0]
    iteration = 1
    logging.info("  Begin iterating through Casualties...")
    for casualty_name in scenario_file['casualties']:
        casualty = scenario_file['casualties'][casualty_name]
        if 'zone' not in casualty:
            logging.info("  No Zone defined in Casualty Scenario Loadout")
            raise Exception("No Zone defined in Casualty Scenario Loadout")
        if 'casualty_type' not in casualty:
            logging.info("  No Type defined in Casualty Scenario Loadout")
            raise Exception("No Type defined in Casualty Scenario Loadout")
        casualty_string = casualty['casualty_type'] + "|" + str(casualty['zone'])
        functor_sent_casualties_bp.set_attribute(str(iteration), casualty_string)
        iteration+=1
    return world.spawn_actor(functor_sent_casualties_bp, global_transform)

def _setup_vehicle_actors(world, scenario_file, bp_library):
    actors = []
    try:
        # vehicle settings, static for P1
        vehicle_type = "waypointvehicle"
        logging.debug(" Spawning vehicle: %s", vehicle_type)
        bp = bp_library.filter(vehicle_type)[0]
        logging.debug(" Setting attributes for: %s", vehicle_type)
        bp.set_attribute("role_name", 'dtc_vehicle')
        bp.set_attribute("ros_name",  'dtc_vehicle')
        logging.debug(" Spawning vehicle in world: %s", vehicle_type)
        vehicle = world.spawn_actor(bp, world.get_map().get_spawn_points()[0], attach_to=None)
        actors.append(vehicle)

        # Create sensors based on this input:
        # This is done manually to ensure that all vehicle and sensor behavior in the simulation is static across runs
        logging.debug(' Creating LiDAR Sensor')
        sensor = bp_library.filter('sensor.lidar.ray_cast')[0]
        sensor.set_attribute("role_name",          'front_lidar')
        sensor.set_attribute("ros_name",           'front_lidar')
        sensor.set_attribute("range",              '50')
        sensor.set_attribute("channels",           '64')
        sensor.set_attribute("points_per_second",  '2621440')
        sensor.set_attribute("rotation_frequency", '20')
        sensor.set_attribute("upper_fov",          '22.5')
        sensor.set_attribute("lower_fov",          '-22.5')
        sensor.set_attribute("sensor_tick",        '0.1')
        sensor_spawn = carla.Transform(location=carla.Location(x=0, y=0, z=1.2), rotation=carla.Rotation(roll=0, pitch=-6.305, yaw=0))
        sensor_actor = world.spawn_actor(sensor, sensor_spawn, attach_to=vehicle)
        sensor_actor.enable_for_ros()
        actors.append(sensor_actor)

        logging.debug(' Creating RADAR Sensor')
        sensor = bp_library.filter('sensor.other.radar')[0]
        sensor.set_attribute("role_name",          'front_radar')
        sensor.set_attribute("ros_name",           'front_radar')
        sensor.set_attribute("horizontal_fov",     '30')
        sensor.set_attribute("vertical_fov",       '30')
        sensor.set_attribute("range",              '50')
        sensor.set_attribute("sensor_tick",        '0.1')
        sensor_spawn = carla.Transform(location=carla.Location(x=0, y=0, z=1.2), rotation=carla.Rotation(roll=0, pitch=-6.305, yaw=0))
        sensor_actor = world.spawn_actor(sensor, sensor_spawn, attach_to=vehicle)
        sensor_actor.enable_for_ros()
        actors.append(sensor_actor)

        logging.debug(' Creating RGB Sensor')
        sensor = bp_library.filter('sensor.camera.rgb')[0]
        sensor.set_attribute("role_name",             'front_rgb')
        sensor.set_attribute("ros_name",              'front_rgb')
        sensor.set_attribute("image_size_x",          '1920')
        sensor.set_attribute("image_size_y",          '1200')
        sensor.set_attribute("fov",                   '90.0')
        sensor.set_attribute("sensor_tick",           '0.05')
        sensor.set_attribute("gamma",                 '1.7')
        sensor.set_attribute("exposure_compensation", '1.5')
        sensor.set_attribute("lens_flare_intensity",  '0.0')
        sensor.set_attribute("temp",                  '6100')
        sensor_spawn = carla.Transform(location=carla.Location(x=0, y=0, z=1.2), rotation=carla.Rotation(roll=0, pitch=-20, yaw=0))
        sensor_actor = world.spawn_actor(sensor, sensor_spawn, attach_to=vehicle)
        sensor_actor.enable_for_ros()
        actors.append(sensor_actor)

        logging.debug(' Creating IR Sensor')
        sensor = bp_library.filter('sensor.camera.ir')[0]
        sensor.set_attribute("role_name",    'front_ir')
        sensor.set_attribute("ros_name",     'front_ir')
        sensor.set_attribute("image_size_x", '1920')
        sensor.set_attribute("image_size_y", '1200')
        sensor.set_attribute("fov",          '90.0')
        sensor.set_attribute("sensor_tick",  '0.05')
        sensor_spawn = carla.Transform(location=carla.Location(x=0, y=0, z=1.2), rotation=carla.Rotation(roll=0, pitch=-20, yaw=0))
        sensor_actor = world.spawn_actor(sensor, sensor_spawn, attach_to=vehicle)
        sensor_actor.enable_for_ros()
        actors.append(sensor_actor)

        logging.debug(' Creating GPS Sensor')
        sensor = bp_library.filter('sensor.other.gnss')[0]
        sensor.set_attribute("role_name",   'gnss')
        sensor.set_attribute("ros_name",    'gnss')
        sensor.set_attribute("sensor_tick", '0.1')
        sensor_spawn = carla.Transform(location=carla.Location(x=0, y=0, z=0), rotation=carla.Rotation(roll=0, pitch=0, yaw=0))
        sensor_actor = world.spawn_actor(sensor, sensor_spawn, attach_to=vehicle)
        sensor_actor.enable_for_ros()
        actors.append(sensor_actor)

        logging.debug(' Creating IMU Sensor')
        sensor = bp_library.filter('sensor.other.imu')[0]
        sensor.set_attribute("role_name",   'imu')
        sensor.set_attribute("ros_name",    'imu')
        sensor.set_attribute("sensor_tick", '0.1')
        sensor_spawn = carla.Transform(location=carla.Location(x=0, y=0, z=0), rotation=carla.Rotation(roll=0, pitch=0, yaw=0))
        sensor_actor = world.spawn_actor(sensor, sensor_spawn, attach_to=vehicle)
        sensor_actor.enable_for_ros()
        actors.append(sensor_actor)

    except Exception as error:
        logging.info('  Error: %s', type(error))
        logging.info('  Error: %s', error)
        raise Exception("Failed to Spawn Vehicle and Sensors")

    return actors

def main(args):
    rclpy.init()
    simulation_status_node = SimulationStatusNode()
    simulation_start_node = SimulationStartNode()
    simulation_audio_node = SimulationAudioNode()
    simulation_gnss_node = SimulationGNSSNode()
    simulation_odom_node = SimulationVehicleOdometryNode()
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(simulation_status_node)
    executor.add_node(simulation_start_node)
    executor.add_node(simulation_audio_node)
    executor.add_node(simulation_gnss_node)
    executor.add_node(simulation_odom_node)
    world = None
    old_world = None
    original_settings = None
    tracked_actors = []
    mission_started = False

    # Spin in a separate thread
    executor_thread = threading.Thread(target=executor.spin, daemon=True)
    executor_thread.start()

    try:
        # Load the Scenario File
        scenario_path = python_file_path + 'scenarios/' + args.file + '.yaml'
        logging.debug(' Loading Scenario File: %s', scenario_path)
        scenario_file = yaml.safe_load(open(scenario_path, 'r'))
        logging.debug('  %s', scenario_file)

        # Setup CARLA World
        logging.debug(' Setting up Carla Client and Settings')
        client = carla.Client(args.host, args.port)
        client.set_timeout(60.0)
        old_world = client.get_world()
        original_settings = old_world.get_settings()
        settings = old_world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 0.05

        # Get and modify the weather
        # weather = old_world.get_weather()            
        # weather.cloudiness=10.000000
        # weather.precipitation=0.00000
        # weather.precipitation_deposits=0.00000
        # weather.wind_intensity=5.000000
        # weather.sun_azimuth_angle=-1.000000
        # weather.sun_altitude_angle=45.000000
        # weather.fog_density=0.000000
        # weather.fog_distance=0.750000
        # weather.fog_falloff=0.250000
        # weather.wetness=0.000000
        # weather.scattering_intensity=1.000000
        # weather.mie_scattering_scale=0.003996
        # weather.rayleigh_scattering_scale=0.033100
        # weather.dust_storm=0.000000

        # Change CARLA Map to desired map
        if 'map' in scenario_file:
            logging.debug(' Checking for Map: %s', scenario_file['map'])
            logging.debug(' Available Map: %s', client.get_available_maps())
            for map in client.get_available_maps():
                if scenario_file['map'] in map:
                    logging.debug(' Loading Map: %s', map)
                    client.load_world(map)
                    world = client.get_world()
                    world.apply_settings(settings)
                    #world.set_weather(weather)
                    break
        else:
            logging.info("  No Map in Scenario File")
            raise Exception("No Map in Scenario File")

        # Create the simulation starter
        bp_library = world.get_blueprint_library()
        functor_start_simulation_bp = bp_library.filter("functorstartsimulation")[0]

        # Setup MetaHumans
        tracked_actors.append(_setup_casualty_actors(world, scenario_file, bp_library))

        # Setup Vehicle Waypoints
        tracked_actors.append(_setup_waypoint_actors(world, scenario_file, bp_library))
        tracked_actors.append(_setup_dwell_time_actors(world, scenario_file, bp_library))

        # Create Vehicle with sensors
        vehicle_actors = _setup_vehicle_actors(world, scenario_file, bp_library)
        if len(vehicle_actors) > 0:
            simulation_odom_node.set_vehicle(vehicle_actors[0])
        for actor in vehicle_actors:
           tracked_actors.append(actor)

        # Setup Audio File To Waypoint Mapping, need to remap from casualty type to the waypoint itself
        # Audio Mapping is {'Zone':'Audio File Name'}
        zone_audio_map = {}
        audio_map = {}
        num_waypoints = 0
        if 'audio_map' in scenario_file:
            for casualty_name in scenario_file['casualties']:
                casualty = scenario_file['casualties'][casualty_name]
                zone_audio_map[str(casualty['zone'])] = scenario_file['audio_map'][casualty['casualty_type']]
            for waypoint_name in scenario_file['waypoints']:
                waypoint = scenario_file['waypoints'][waypoint_name]
                num_waypoints+=1
                audio_map[str(num_waypoints)] = zone_audio_map[str(waypoint['zone'])]
        else:
            logging.info("  No Audio Mapping in Scenario File")
            raise Exception("No Audio Mapping in Scenario File")
        logging.debug(" Audio Mapping: %s", audio_map)

        # Start Simulation, need to process a second of frames to fully load things
        logging.info("  Starting Simulation...")
        for step in range(20):
            _ = world.tick()
        simulation_status_node.set_status(True)
        stationary_count = 0
        while True:
            try:
                # Check if the simulation has not been started but should, if so, trigger the start command in Unreal
                if not mission_started and simulation_start_node.get_start():
                    logging.info("  Running Mission...")
                    tracked_actors.append(world.spawn_actor(functor_start_simulation_bp, global_transform))
                    mission_started = True
                    simulation_gnss_node.start_tracking()
                    simulation_odom_node.set_start()

                # Tick the simulation if the mission has been started, otherwise, wait for the start command
                if mission_started:
                    _ = world.tick()
                else:
                    time.sleep(settings.fixed_delta_seconds)
                    # Ensures that rogue messages on startup don't contribute to stationary counts
                    stationary_count=0

                # Check if the vehicle is stationary, if not, reset the stationary count
                if simulation_gnss_node.get_is_stationary():
                    stationary_count+=1
                else:
                    stationary_count=0
                
                # Get the current waypoint, if not 0, set the audio file name that should be published
                if simulation_gnss_node.get_current_waypoint() != 0 and not simulation_gnss_node.get_current_waypoint() > num_waypoints:
                    # Since waypoint order is not sequential, we need to check this waypoint against the actual zone it maps to
                    simulation_audio_node.set_audio(str(audio_map[str(simulation_gnss_node.get_current_waypoint())]))
                
                # Check if the vehicle has been stationary long enough to close the simulation (5 seconds)
                if stationary_count >= 5 / settings.fixed_delta_seconds and simulation_gnss_node.get_current_waypoint() >= num_waypoints:
                    logging.info("  Mission Completed... Completed all Waypoints")
                    break

                if simulation_start_node.check_timeout():
                    logging.info("  Mission Completed... Exceeded Time Limit")
                    break

            except:
                logging.info('  CARLA Client no longer connected, likely a system crash or the mission completed')
                raise Exception("CARLA Client no longer connected")
    except KeyboardInterrupt:
        logging.info('  System Shutdown Command, closing out System Manager')
    except Exception as error:
        logging.info('  Error: %s', error)
        logging.info('  System Error, Check log, likely CARLA is not connected. See if CARLA is running.')

    finally:
        try:
            if args.cleankill:
                logging.info('  Clean Kill enabled, End World...')
                if original_settings:
                    client.get_world().apply_settings(original_settings)
                    _ = world.tick()
                    client.load_world('EndingWorld')
                logging.info('  Game Instance Closed, exiting System Manager...')
            else:
                logging.info('  Reseting Game to original state...')
                for actor in tracked_actors:
                    actor.destroy()

                if original_settings:
                    client.load_world('StartingWorld')
                    client.get_world().apply_settings(original_settings)

                _ = world.tick()
                logging.info('  Game finished resetting, exiting System Manager...')
        except Exception as error:
            logging.info('  Error: %s', error)
            logging.info('  Failed to reset game to original state...')
            pass

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='DTC System Manager')
    argparser.add_argument('--host',          default='localhost', dest='host',      type=str,  help='IP of the host CARLA Simulator (default: localhost)')
    argparser.add_argument('--port',          default=2000,        dest='port',      type=int,  help='TCP port of CARLA Simulator (default: 2000)')
    argparser.add_argument('-f', '--file',    default='example',   dest='file',      type=str,  help='Scenario File to run, Note, Always looks in `dtc_manager/scenarios` and does not include the .yaml (default: example)')
    argparser.add_argument('-v', '--verbose', default=False,       dest='verbose',   type=bool, help='print debug information (default: False)')
    argparser.add_argument('--clean-kill',    default=False,       dest='cleankill', type=bool, help='When true, cleanly kills the simulation when the python script is exited')

    args = argparser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(filename=python_file_path + 'dtc_manager.log', level=log_level)
    with open(python_file_path + 'dtc_manager.log', 'w'):
        pass
    logging.info('  Starting DTC System Manager')
    logging.debug(' Listening to server %s:%s', args.host, args.port)

    main(args)

    print(open(python_file_path + "dtc_manager.log", "r").read())
