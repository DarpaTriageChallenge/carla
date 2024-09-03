#pragma once

#include "carla/MsgPack.h"

namespace carla {
namespace rpc {

  class RotorPhysicsControl {
  public:

    RotorPhysicsControl() = default;

    RotorPhysicsControl(
        float in_thrust_coefficient,
        float in_torque_coefficient,
        float in_max_rpm,
        float in_propeller_diameter,
        float in_propeller_height,
        bool in_clockwise)
      : thrust_coefficient(in_thrust_coefficient),
        torque_coefficient(in_torque_coefficient),
        max_rpm(in_max_rpm),
        propeller_diameter(in_propeller_diameter),
        propeller_height(in_propeller_height),
        clockwise(in_clockwise) {}

    float thrust_coefficient = 0.109919F;
    float torque_coefficient = 0.040164F;
    float max_rpm = 6936.667F;
    float propeller_diameter = 0.2286F;
    float propeller_height = 0.01F;
    bool clockwise = true;

#ifdef LIBCARLA_INCLUDED_FROM_UE4
    RotorPhysicsControl(const FRotorSetup& Rotor)
        : thrust_coefficient(Rotor.ThrustCoefficient),
          torque_coefficient(Rotor.TorqueCoefficient),
          max_rpm(Rotor.MaxRPM),
          propeller_diameter(Rotor.PropellerDiameter),
          propeller_height(Rotor.PropellerHeight),
          clockwise(Rotor.Clockwise) {}

    operator FRotorSetup() const {
        FRotorSetup Rotor;
        Rotor.ThrustCoefficient = thrust_coefficient;
        Rotor.TorqueCoefficient = torque_coefficient;
        Rotor.MaxRPM = max_rpm;
        Rotor.PropellerDiameter = propeller_diameter;
        Rotor.PropellerHeight = propeller_height;
        Rotor.Clockwise = clockwise;
        return Rotor;
    }
#endif

    MSGPACK_DEFINE_ARRAY(
        thrust_coefficient,
        torque_coefficient,
        max_rpm,
        propeller_diameter,
        propeller_height,
        clockwise)
  };

}
}
