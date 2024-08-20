#pragma once

#include "MultirotorControl.generated.h"

USTRUCT(BlueprintType)
struct CARLA_API FMultirotorControl
{
    GENERATED_BODY()

    UPROPERTY(Category = "Multirotor Control", EditAnywhere, BlueprintReadWrite)
    TArray<float> Throttle; // [0, 1]
};

