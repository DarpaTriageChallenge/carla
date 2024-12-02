#pragma once

#include "RotorSetup.h"

#include "MultirotorPhysicsControl.generated.h"

USTRUCT(BlueprintType)
struct CARLA_API FMultirotorPhysicsControl
{
    GENERATED_BODY()

    UPROPERTY(Category = "Rotor Setup", EditAnywhere, BlueprintReadWrite)
    TArray<FRotorSetup> Rotors;
};

