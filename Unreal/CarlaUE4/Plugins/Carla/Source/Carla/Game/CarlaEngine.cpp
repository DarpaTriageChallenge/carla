// Copyright (c) 2017 Computer Vision Center (CVC) at the Universitat Autonoma
// de Barcelona (UAB).
//
// This work is licensed under the terms of the MIT license.
// For a copy, see <https://opensource.org/licenses/MIT>.

#include "Carla.h"
#include "Carla/Game/CarlaEngine.h"

#include "Carla/Game/CarlaEpisode.h"
#include "Carla/Game/CarlaStaticDelegates.h"
#include "Carla/Lights/CarlaLightSubsystem.h"
#include "Carla/Recorder/CarlaRecorder.h"
#include "Carla/Settings/CarlaSettings.h"
#include "Carla/Settings/EpisodeSettings.h"

#include "Runtime/Core/Public/Misc/App.h"
#include "PhysicsEngine/PhysicsSettings.h"
#include "Carla/MapGen/LargeMapManager.h"

#include <compiler/disable-ue4-macros.h>
#include <carla/multigpu/primaryCommands.h>
#include <carla/multigpu/secondary.h>
#include <carla/multigpu/secondaryCommands.h>
#include <compiler/enable-ue4-macros.h>

#include <thread>

// =============================================================================
// -- Static local methods -----------------------------------------------------
// =============================================================================

// init static frame counter
uint64_t FCarlaEngine::FrameCounter = 0;

static uint32 FCarlaEngine_GetNumberOfThreadsForRPCServer()
{
  return std::max(std::thread::hardware_concurrency(), 4u) - 2u;
}

static TOptional<double> FCarlaEngine_GetFixedDeltaSeconds()
{
  return FApp::IsBenchmarking() ? FApp::GetFixedDeltaTime() : TOptional<double>{};
}

static void FCarlaEngine_SetFixedDeltaSeconds(TOptional<double> FixedDeltaSeconds)
{
  FApp::SetBenchmarking(FixedDeltaSeconds.IsSet());
  FApp::SetFixedDeltaTime(FixedDeltaSeconds.Get(0.0));
}

// =============================================================================
// -- FCarlaEngine -------------------------------------------------------------
// =============================================================================

FCarlaEngine::~FCarlaEngine()
{
  if (bIsRunning)
  {
    FWorldDelegates::OnWorldTickStart.Remove(OnPreTickHandle);
    FWorldDelegates::OnWorldPostActorTick.Remove(OnPostTickHandle);
    FCarlaStaticDelegates::OnEpisodeSettingsChange.Remove(OnEpisodeSettingsChangeHandle);
  }
}

void FCarlaEngine::NotifyInitGame(const UCarlaSettings &Settings)
{
  TRACE_CPUPROFILER_EVENT_SCOPE_STR(__FUNCTION__);
  if (!bIsRunning)
  {
    const auto StreamingPort = Settings.StreamingPort;
    const auto SecondaryPort = Settings.SecondaryPort;
    const auto PrimaryIP     = Settings.PrimaryIP;
    const auto PrimaryPort   = Settings.PrimaryPort;
    
    auto BroadcastStream     = Server.Start(Settings.RPCPort, StreamingPort, SecondaryPort);
    Server.AsyncRun(FCarlaEngine_GetNumberOfThreadsForRPCServer());

    WorldObserver.SetStream(BroadcastStream);

    OnPreTickHandle = FWorldDelegates::OnWorldTickStart.AddRaw(
        this,
        &FCarlaEngine::OnPreTick);
    OnPostTickHandle = FWorldDelegates::OnWorldPostActorTick.AddRaw(
        this,
        &FCarlaEngine::OnPostTick);
    OnEpisodeSettingsChangeHandle = FCarlaStaticDelegates::OnEpisodeSettingsChange.AddRaw(
        this,
        &FCarlaEngine::OnEpisodeSettingsChanged);

    bIsRunning = true;

    // check to convert this as secondary server
    if (!PrimaryIP.empty())
    {
      Secondary = std::make_shared<carla::multigpu::Secondary>(PrimaryIP, PrimaryPort, std::bind(&carla::multigpu::SecondaryCommands::on_command, &SecCommander, std::placeholders::_1));
      SecCommander.set_secondary(Secondary);
      Secondary->Connect();
    }
    else
    {
      SecondaryServer = Server.GetSecondaryServer();
      Commander.set_router(SecondaryServer);
    }
  }

  bMapChanged = true;

}

void FCarlaEngine::NotifyBeginEpisode(UCarlaEpisode &Episode)
{
  TRACE_CPUPROFILER_EVENT_SCOPE_STR(__FUNCTION__);
  Episode.EpisodeSettings.FixedDeltaSeconds = FCarlaEngine_GetFixedDeltaSeconds();
  CurrentEpisode = &Episode;

  CurrentEpisode->ApplySettings(CurrentSettings);

  ResetFrameCounter(GFrameNumber);

  // make connection between Episode and Recorder
  if (Recorder)
  {
    Recorder->SetEpisode(&Episode);
    Episode.SetRecorder(Recorder);
    Recorder->GetReplayer()->CheckPlayAfterMapLoaded();
  }

  Server.NotifyBeginEpisode(Episode);
}

void FCarlaEngine::NotifyEndEpisode()
{
  Server.NotifyEndEpisode();
  CurrentEpisode = nullptr;
}

void FCarlaEngine::OnPreTick(UWorld *, ELevelTick TickType, float DeltaSeconds)
{
  TRACE_CPUPROFILER_EVENT_SCOPE_STR(__FUNCTION__);
  if (TickType == ELevelTick::LEVELTICK_All)
  {
    // update frame counter
    UpdateFrameCounter();

    // process RPC commands
    do
    {
      Server.RunSome(10u);
    }
    while (bSynchronousMode && !Server.TickCueReceived());

    if (CurrentEpisode != nullptr)
    {
      CurrentEpisode->TickTimers(DeltaSeconds);
    }
  }
}


void FCarlaEngine::OnPostTick(UWorld *World, ELevelTick TickType, float DeltaSeconds)
{
  TRACE_CPUPROFILER_EVENT_SCOPE_STR(__FUNCTION__);
  // tick the recorder/replayer system
  if (GetCurrentEpisode())
  {
    if (bIsPrimaryServer)
    {
      GetCurrentEpisode()->GetFrameData().GetFrameData(GetCurrentEpisode());
      std::ostringstream OutStream;
      GetCurrentEpisode()->GetFrameData().Write(OutStream);
      // OutStream.str()
      // send frame data to secondary
      GetCurrentEpisode()->GetFrameData().Clear();
    }
    else
    {
      // play frame data
      // get frame data from primary
      std::istringstream InStream;
      // InStream.str(InStr);
      GetCurrentEpisode()->GetFrameData().Read(InStream);
      GetCurrentEpisode()->GetFrameData().PlayFrameData(GetCurrentEpisode(), MappedId);
      GetCurrentEpisode()->GetFrameData().Clear();
    }

    auto* EpisodeRecorder = GetCurrentEpisode()->GetRecorder();
    if (EpisodeRecorder)
    {
      EpisodeRecorder->Ticking(DeltaSeconds);
    }
  }

  if ((TickType == ELevelTick::LEVELTICK_All) && (CurrentEpisode != nullptr))
  {
    // Look for lightsubsystem
    bool LightUpdatePending = false;
    if (World)
    {
      UCarlaLightSubsystem* CarlaLightSubsystem = World->GetSubsystem<UCarlaLightSubsystem>();
      if (CarlaLightSubsystem)
      {
        LightUpdatePending = CarlaLightSubsystem->IsUpdatePending();
      }
    }

    if (SecondaryServer->IsMultiGPU()) {
      Commander.SendFrameData(carla::Buffer());
    }

    // send the worldsnapshot
    WorldObserver.BroadcastTick(*CurrentEpisode, DeltaSeconds, bMapChanged, LightUpdatePending);
    ResetSimulationState();
  }
}

void FCarlaEngine::OnEpisodeSettingsChanged(const FEpisodeSettings &Settings)
{
  CurrentSettings = FEpisodeSettings(Settings);

  bSynchronousMode = Settings.bSynchronousMode;

  if (GEngine && GEngine->GameViewport)
  {
    GEngine->GameViewport->bDisableWorldRendering = Settings.bNoRenderingMode;
  }

  FCarlaEngine_SetFixedDeltaSeconds(Settings.FixedDeltaSeconds);

  // Setting parameters for physics substepping
  UPhysicsSettings* PhysSett = UPhysicsSettings::Get();
  PhysSett->bSubstepping = Settings.bSubstepping;
  PhysSett->MaxSubstepDeltaTime = Settings.MaxSubstepDeltaTime;
  PhysSett->MaxSubsteps = Settings.MaxSubsteps;

  UWorld* World = CurrentEpisode->GetWorld();
  ALargeMapManager* LargeMapManager = UCarlaStatics::GetLargeMapManager(World);
  if (LargeMapManager)
  {
    LargeMapManager->SetLayerStreamingDistance(Settings.TileStreamingDistance);
    LargeMapManager->SetActorStreamingDistance(Settings.ActorActiveDistance);
  }
}

void FCarlaEngine::ResetSimulationState()
{
  bMapChanged = false;
}
