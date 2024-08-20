#pragma once

#include "carla/MsgPack.h"

#ifdef LIBCARLA_INCLUDED_FROM_UE4
#include <compiler/enable-ue4-macros.h>
#  include "Carla/Multirotor/MultirotorControl.h"
#include <compiler/disable-ue4-macros.h>
#endif // LIBCARLA_INCLUDED_FROM_UE4

namespace carla {
namespace rpc { 

  class MultirotorControl {
  public:

    MultirotorControl() = default;

    MultirotorControl(
        std::vector<float> in_throttle)
      : throttle(in_throttle) {}

    std::vector<float> throttle;

#ifdef LIBCARLA_INCLUDED_FROM_UE4

    MultirotorControl(const FMultirotorControl &Control)
    {
        throttle.clear();
        for (const auto& ThrottleValue: Control.Throttle)
        {
            throttle.push_back(ThrottleValue);
        }
    }

    operator FMultirotorControl() const {
      FMultirotorControl Control;
      TArray<float> Throttle;
      for (const auto& ThrottleValue : throttle)
      {
          Throttle.Add(ThrottleValue);
      }
      Control.Throttle = Throttle;

      return Control;
    }

#endif // LIBCARLA_INCLUDED_FROM_UE4

    bool operator!=(const MultirotorControl &rhs) const {
      return throttle != rhs.throttle;
    }

    bool operator==(const MultirotorControl &rhs) const {
      return !(*this != rhs);
    }

    MSGPACK_DEFINE_ARRAY(
        throttle)
  };

} // namespace rpc
} // namespace carla
