/*
 * OBS Preply Plugin — Session recorder with virtual camera + subtitles
 * Copyright (C) 2025 GYCinc
 */
#include <obs-module.h>
#include <obs-frontend-api.h>

OBS_DECLARE_MODULE()
OBS_MODULE_USE_DEFAULT_LOCALE("obs-preply", "en-US")

static obs_output_t  *recording   = NULL;
static bool            is_recording = false;

static void start_preply_session(void)
{
	struct obs_output_info info = {
		.id    = "ffmpeg_muxer",
		.flags = OBS_OUTPUT_VIDEO | OBS_OUTPUT_AUDIO | OBS_OUTPUT_ENCODED,
	};
	obs_data_t *settings = obs_data_create();
	obs_data_set_string(settings, "path", "");
	recording = obs_output_create("ffmpeg_mkv_output", "preply", settings, NULL);
	if (recording) {
		obs_output_start(recording);
		is_recording = true;
		obs_log(LOG_INFO, "Preply session recording started");
	}
	obs_data_release(settings);
}

static void stop_preply_session(void)
{
	if (recording && is_recording) {
		obs_output_stop(recording);
		obs_output_release(recording);
		recording   = NULL;
		is_recording = false;
		obs_log(LOG_INFO, "Preply session recording stopped");
	}
}

bool obs_module_load(void)
{
	obs_frontend_add_event_callback(
		[](enum obs_frontend_event event, void *) {
			switch (event) {
			case OBS_FRONTEND_EVENT_RECORDING_STARTING:
				obs_log(LOG_INFO, "Recording starting via frontend");
				break;
			case OBS_FRONTEND_EVENT_RECORDING_STOPPED:
				obs_log(LOG_INFO, "Recording stopped via frontend");
				break;
			default: break;
			}
		},
		NULL);
	obs_log(LOG_INFO, "obs-preply loaded");
	return true;
}

void obs_module_unload(void)
{
	stop_preply_session();
	obs_log(LOG_INFO, "obs-preply unloaded");
}
