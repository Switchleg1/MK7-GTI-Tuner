Background music — drop song files here.

One folder per stage; the game picks a RANDOM song from the matching folder, and
when it finishes it plays another random one from the same folder. A "NOW PLAYING"
toast pops when each song starts. Supported: .ogg / .mp3 / .wav (.ogg is the safest
in a packaged build). An empty/missing folder just means silence for that stage.

Folder        Stage
------------  -------------------------------------
tuning/       TUNE (the maps/tuning task)
skreetz/      SKREETS (the street task)
dyno/         DYNO
race/         RACE
shop/         SHOP
bench/        BENCH
garage/       the garage hub
unlock/       the ECU-unlock cinematic

(The folder name is each stage's `music_key`; for most stages that's just the task
key, but TUNE -> "tuning" and SKREETS -> "skreetz" use the themed names.)
