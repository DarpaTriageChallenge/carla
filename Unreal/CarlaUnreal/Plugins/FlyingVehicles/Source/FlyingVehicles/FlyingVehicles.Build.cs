using UnrealBuildTool;
using System.IO;

public class FlyingVehicles : ModuleRules
{
    public FlyingVehicles(ReadOnlyTargetRules Target) : base(Target)
    {
        bEnableExceptions = true;
        PrivatePCHHeaderFile = "FlyingVehicles.h";

        PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "PhysicsCore", "Carla", "Chaos", "ChaosVehicles",
        "Foliage",
      "HTTP",
      "StaticMeshDescription",
      "ImageWriteQueue",
      "Json",
      "JsonUtilities",
      "Landscape",
      "Slate",
      "SlateCore",
      "RHI",
      "Renderer",
      "ProceduralMeshComponent",
      "MeshDescription" });

        if (Target.Type == TargetType.Editor)
        {
            PublicDependencyModuleNames.AddRange(new string[] { "UnrealEd" });
        }

        PrivateDependencyModuleNames.AddRange(new string[] {  });
    }
}
