using UnrealBuildTool;
using System.IO;

public class Multirotors : ModuleRules
{
    public Multirotors(ReadOnlyTargetRules Target) : base(Target)
    {
        DefaultBuildSettings = BuildSettingsVersion.V2;

        PrivatePCHHeaderFile = "Multirotors.h";

        PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "PhysicsCore", "PhysX" });

        if (Target.Type == TargetType.Editor)
        {
            PublicDependencyModuleNames.AddRange(new string[] { "UnrealEd" });
        }

        PrivateDependencyModuleNames.AddRange(new string[] {  });
    }
}
