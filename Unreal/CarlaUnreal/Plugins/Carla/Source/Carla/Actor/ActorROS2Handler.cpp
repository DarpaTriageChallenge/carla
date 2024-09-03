// Copyright (c) 2024 Computer Vision Center (CVC) at the Universitat Autonoma
// de Barcelona (UAB).
//
// This work is licensed under the terms of the MIT license.
// For a copy, see <https://opensource.org/licenses/MIT>.

#include "ActorROS2Handler.h"

#include "Carla/Multirotor/MultirotorPawn.h"
#include "Carla/Multirotor/MultirotorControl.h"
#include "Carla/Vehicle/CarlaWheeledVehicle.h"
#include "Carla/Vehicle/VehicleControl.h"

void ActorROS2Handler::operator()(carla::ros2::VehicleControl &Source)
{
  if (!_Actor) return;

  ACarlaWheeledVehicle *Vehicle = Cast<ACarlaWheeledVehicle>(_Actor);
  if (!Vehicle) return;

  // setup control values
  FVehicleControl NewControl;
  NewControl.Throttle = Source.throttle;
  NewControl.Steer = Source.steer;
  NewControl.Brake = Source.brake;
  NewControl.bHandBrake = Source.hand_brake;
  NewControl.bReverse = Source.reverse;
  NewControl.bManualGearShift = Source.manual_gear_shift;
  NewControl.Gear = Source.gear;

  Vehicle->ApplyVehicleControl(NewControl, EVehicleInputPriority::User);
}

void ActorROS2Handler::operator()(carla::ros2::MultirotorControl &Source)
{
  if (!_Actor) return;

  AMultirotorPawn *Multirotor = Cast<AMultirotorPawn>(_Actor);
  if (!Multirotor) return;

  // setup control values
  FMultirotorControl NewControl;
  TArray<float> newThrottle;
  newThrottle.SetNumUninitialized(Source.throttle.size());
  for (int i = 0; i < Source.throttle.size(); i++){
    newThrottle[i] = Source.throttle[i];
  }
  NewControl.Throttle = newThrottle;

  Multirotor->ApplyMultirotorControl(NewControl);
}

void ActorROS2Handler::operator()(carla::ros2::MessageControl Message)
{
  if (!_Actor) return;

  ACarlaWheeledVehicle *Vehicle = Cast<ACarlaWheeledVehicle>(_Actor);
  if (!Vehicle) return;

  Vehicle->PrintROS2Message(Message.message);

  // FString ROSMessage = Message.message;
  // UE_LOG(LogCarla, Warning, TEXT("ROS2 Message received: %s"), *ROSMessage);
}
