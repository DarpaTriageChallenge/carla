#include "carla/client/Multirotor.h"

#include "carla/client/ActorList.h"
#include "carla/client/detail/Simulator.h"
#include "carla/Memory.h"

namespace carla {
namespace client {

  Multirotor::Multirotor(ActorInitializer init)
    : Actor(std::move(init)) {}


  void Multirotor::ApplyControl(const Control &control) {
    if (control != _control) {
      GetEpisode().Lock()->ApplyControlToMultirotor(*this, control);
      _control = control;
    }
  }

  void Multirotor::ApplyPhysicsControl(const PhysicsControl &physics_control) {
    GetEpisode().Lock()->ApplyPhysicsControlToMultirotor(*this, physics_control);
  }

  Multirotor::Control Multirotor::GetControl() const {
    return GetEpisode().Lock()->GetActorSnapshot(*this).state.multirotor_data.control;
  }

  Multirotor::PhysicsControl Multirotor::GetPhysicsControl() const {
    return GetEpisode().Lock()->GetMultirotorPhysicsControl(*this);
  }


} // namespace client
} // namespace carla
