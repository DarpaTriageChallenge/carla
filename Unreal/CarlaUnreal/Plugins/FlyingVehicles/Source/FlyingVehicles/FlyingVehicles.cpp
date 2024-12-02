#include "FlyingVehicles.h"

#include "CarlaActor.h"

#define LOCTEXT_NAMESPACE "FFlyingVehicles"


DEFINE_LOG_CATEGORY(LogFlyingVehicles)

void FFlyingVehicles::StartupModule()
{
    FMultirotorActor::RegisterClassWithFactory();
}

void FFlyingVehicles::ShutdownModule()
{
}

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FFlyingVehicles, FlyingVehicles)

