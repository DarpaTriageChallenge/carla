#pragma once

#include "carla/MsgPack.h"
#include "carla/rpc/RotorPhysicsControl.h"

#include <vector>

#ifdef LIBCARLA_INCLUDED_FROM_UE4
#include <compiler/enable-ue4-macros.h>
#  include "MultirotorPhysicsControl.h"
#include <compiler/disable-ue4-macros.h>
#endif

namespace carla {
namespace rpc {

  class MultirotorPhysicsControl {
  public:

    MultirotorPhysicsControl() = default;

    MultirotorPhysicsControl(
        std::vector<RotorPhysicsControl> in_rotors)
      : rotors(in_rotors) {}

    std::vector<RotorPhysicsControl> rotors;

#ifdef LIBCARLA_INCLUDED_FROM_UE4
    MultirotorPhysicsControl(const FMultirotorPhysicsControl& Control)
    {
        rotors.clear();
        for (const auto &Rotor : Control.Rotors) {
          rotors.push_back(RotorPhysicsControl(Rotor));
        }
    }

    operator FMultirotorPhysicsControl() const {
        FMultirotorPhysicsControl Physics;
        TArray<FRotorSetup> Rotors;
        for (const auto &rotor : rotors) {
            Rotors.Add(FRotorSetup(rotor));
        }
        Physics.Rotors = Rotors;
        return Physics;
    }
#endif

    MSGPACK_DEFINE_ARRAY(
        rotors)
  };

}
}
