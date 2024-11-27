// Copyright (c) 2024 Computer Vision Center (CVC) at the Universitat Autonoma
// de Barcelona (UAB).
//
// This work is licensed under the terms of the MIT license.
// For a copy, see <https://opensource.org/licenses/MIT>.

#include "carla/Logging.h"
#include <carla/ros2/ROS2Interfaces.h>
#include "carla/ros2/ROS2.h"
#include "carla/geom/GeoLocation.h"
#include "carla/geom/Vector3D.h"
#include "carla/sensor/data/DVSEvent.h"
#include "carla/sensor/data/LidarData.h"
#include "carla/sensor/data/SemanticLidarData.h"
#include "carla/sensor/data/RadarData.h"
#include "carla/sensor/data/Image.h"
#include "carla/sensor/s11n/ImageSerializer.h"
#include "carla/sensor/s11n/SensorHeaderSerializer.h"

#include "publishers/CarlaPublisher.h"
#include "publishers/CarlaClockPublisher.h"
#include "publishers/CarlaRGBCameraPublisher.h"
#include "publishers/CarlaDepthCameraPublisher.h"
#include "publishers/CarlaNormalsCameraPublisher.h"
#include "publishers/CarlaOpticalFlowCameraPublisher.h"
#include "publishers/CarlaSSCameraPublisher.h"
#include "publishers/CarlaISCameraPublisher.h"
#include "publishers/CarlaDVSCameraPublisher.h"
#include "publishers/CarlaLidarPublisher.h"
#include "publishers/CarlaSemanticLidarPublisher.h"
#include "publishers/CarlaRadarPublisher.h"
#include "publishers/CarlaIMUPublisher.h"
#include "publishers/CarlaGNSSPublisher.h"
#include "publishers/CarlaMapSensorPublisher.h"
#include "publishers/CarlaSpeedometerSensor.h"
#include "publishers/CarlaTransformPublisher.h"
#include "publishers/CarlaCollisionPublisher.h"
#include "publishers/CarlaLineInvasionPublisher.h"
#include "publishers/BasicPublisher.h"

#include "subscribers/CarlaSubscriber.h"
#include "subscribers/CarlaEgoVehicleControlSubscriber.h"
#if defined(WITH_ROS2_DEMO)
  #include "subscribers/BasicSubscriber.h"
#endif

#include <vector>

namespace carla {
namespace ros2 {

// static fields
std::shared_ptr<ROS2Interfaces> ROS2Interfaces::_instance;

void ROS2Interfaces::Enable(bool enabled)
{
  bool needToCleanInterfaces = false;
  for (std::weak_ptr<ROS2> interfaceWeakPtr : _interfaces)
  {
    if (std::shared_ptr<ROS2> interfacePtr = interfaceWeakPtr.lock())
    {
      interfacePtr->Enable(enabled);
    }
    else
    {
      needToCleanInterfaces = true;
    }
    
  }
  if (needToCleanInterfaces)
  {
    CleanExpiredInterfaces();
  }
}

void ROS2Interfaces::Shutdown(){
  bool needToCleanInterfaces = false;
  for (std::weak_ptr<ROS2> interfaceWeakPtr : _interfaces)
  {
    if (std::shared_ptr<ROS2> interfacePtr = interfaceWeakPtr.lock())
    {
      if (interfacePtr->IsEnabled())
        interfacePtr->Shutdown();
    }
    else
    {
      needToCleanInterfaces = true;
    }
  }

  if (needToCleanInterfaces)
  {
    CleanExpiredInterfaces();
  }
    
}

void ROS2Interfaces::SetFrame(uint64_t frame)
{
  bool needToCleanInterfaces = false;
  for (std::weak_ptr<ROS2> interfaceWeakPtr : _interfaces)
  {
    if (std::shared_ptr<ROS2> interfacePtr = interfaceWeakPtr.lock())
    {
      interfacePtr->SetFrame(frame);
    }
    else
    {
      needToCleanInterfaces = true;
    }
  }
  if (needToCleanInterfaces)
  {
    CleanExpiredInterfaces();
  }
}

void ROS2Interfaces::SetTimestamp(double timestamp)
{
  bool needToCleanInterfaces = false;
  for (std::weak_ptr<ROS2> interfaceWeakPtr : _interfaces)
  {
    if (std::shared_ptr<ROS2> interfacePtr = interfaceWeakPtr.lock())
    {
      interfacePtr->SetTimestamp(timestamp);
    }
    else
    {
      needToCleanInterfaces = true;
    }
  }
  if (needToCleanInterfaces)
  {
    CleanExpiredInterfaces();
  }
}

void ROS2Interfaces::RegisterInterface(std::shared_ptr<ROS2> newInterface)
{
  _interfaces.push_back(newInterface);
}

void ROS2Interfaces::CleanExpiredInterfaces()
{
  _interfaces.erase(std::remove_if(_interfaces.begin(), _interfaces.end(),
    [](const std::weak_ptr<ROS2>& weakPtr) {
        return weakPtr.expired();
    }),
    _interfaces.end());
  
}

void ROS2Interfaces::UnregisterInterface(std::shared_ptr<ROS2> interfaceToRemove)
{
  _interfaces.erase(std::remove_if(_interfaces.begin(), _interfaces.end(),
        [&interfaceToRemove](const std::weak_ptr<ROS2>& weakPtr) {
            if (auto sp = weakPtr.lock()) {
                return sp == interfaceToRemove; 
            }
            return false; // Skip expired weak_ptrs
        }),
        _interfaces.end());
}

} // namespace ros2
} // namespace carla
