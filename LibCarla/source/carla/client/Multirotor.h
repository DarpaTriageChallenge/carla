#pragma once

#include "carla/client/Actor.h"
#include "carla/rpc/MultirotorControl.h"
#include "carla/rpc/MultirotorPhysicsControl.h"


namespace carla {
namespace client {

  class Multirotor: public Actor {
  public:

    using Control = rpc::MultirotorControl;
    using PhysicsControl = rpc::MultirotorPhysicsControl;

    explicit Multirotor(ActorInitializer init);

    /// Apply @a control to this vehicle.
    void ApplyControl(const Control &control);

    /// Apply physics control to this vehicle.
    void ApplyPhysicsControl(const PhysicsControl &physics_control);

    /// Return the control last applied to this vehicle.
    ///
    /// @note This function does not call the simulator, it returns the data
    /// received in the last tick.
    Control GetControl() const;

    /// Return the physics control last applied to this vehicle.
    ///
    /// @warning This function does call the simulator.
    PhysicsControl GetPhysicsControl() const;

  private:
    Control _control;
  };
  
} // namespace client
} // namespace carla
