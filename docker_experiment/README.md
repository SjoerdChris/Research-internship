start the docker locally:
docker compose -f compose.yaml -f compose.local.yaml up --build

Start the docker of Radboud:
cd "/mnt/c/Users/Asus/Documents/Master 2025-2026/internship/docker_experiment"

docker compose build

uc deploy sjoerd-experiment-app

uc ls

uc logs sjoerd-experiment-app

(if wsl == newly_opened):
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
ssh -MNf lilo-radboud

uc ls