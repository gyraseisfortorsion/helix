# Evo 2 setup

Evo 2 is the model; NVIDIA NIM packages it as an API server. Nebius or Brev can supply the GPU when you host that server yourself. Chat and AlphaGenome work independently of Evo 2.

## NVIDIA-hosted API: try this first

1. Sign in on [NVIDIA's Evo 2 7B forward page](https://build.nvidia.com/arc/evo2-7b-forward), select **Get API Key**, and confirm access to this model. Hosted API access is separate from GPU rental credits.
2. Add the following to the **existing** repository-root `.env`, preserving the other keys:

```dotenv
EVO2_FORWARD_URL=https://health.api.nvidia.com/v1/biology/arc/evo2-7b/forward
EVO2_ACCESS_TOKEN=your_nvidia_api_key
EVO2_BASE_URL=
```

3. Restart the backend with `uv run --all-extras helix-api`.
4. In **Genetic findings**, investigate an observed variant and choose **Evo 2**. Start with the synthetic demo; real profiles require external-analysis consent.

The complete `EVO2_FORWARD_URL` takes precedence over `EVO2_BASE_URL`. Helix sends `EVO2_ACCESS_TOKEN` as a bearer token. No GPU instance is needed on your side when this hosted service is available to your account.

Authenticated hosted inference was verified using a synthetic sequence, followed by a complete browser-to-model investigation of the synthetic rs143383 call (8,192-base windows, both strands). The running hosted server uses native `unembed` logits (`unembed.output`, shape `[batch, sequence, 512]`), whereas the current API reference describes the self-hosted NIM 2.x `output_layer` format. Helix handles both explicitly. Automated tests cover both layouts, the bearer header, next-token alignment and non-finite rejection.

## Self-hosting on a Nebius or Brev GPU

Use this if hosted access is unavailable or you want control of the GPU service. Choose **7B on one H100 80GB**. NVIDIA lists a minimum of 50 GB disk and 16 GB CPU RAM; allow extra disk for downloads/cache. The default 40B NIM needs two H100 80GB GPUs or one H200.

These commands assume a Linux x86_64 GPU **VM with SSH**, Docker, NVIDIA drivers and NVIDIA Container Toolkit. The event's shared Nebius Cloud AI offering submits jobs; its container/service-access instructions may differ. Do not assume a submitted job exposes an SSH VM. The separate Nebius Scientific AI Platform is managed model hosting; its Evo 2 availability has not been checked.

On the **GPU server**:

```bash
nvidia-smi
docker run --rm --runtime=nvidia --gpus all ubuntu nvidia-smi

# Enter an NGC key with registry/model access, without printing it.
read -r -s -p "NGC API key: " NGC_API_KEY
export NGC_API_KEY
printf '\n'
printf '%s' "$NGC_API_KEY" | docker login nvcr.io --username '$oauthtoken' --password-stdin

# Choose a persistent cache on a disk with enough free space.
export LOCAL_NIM_CACHE="$PWD/evo2-model-cache"
mkdir -p "$LOCAL_NIM_CACHE"
chmod 0777 "$LOCAL_NIM_CACHE"

docker run -d --name evo2-nim --restart unless-stopped \
  --runtime=nvidia --gpus '"device=0"' \
  -e NGC_API_KEY -e NIM_VARIANT=7b \
  -v "$LOCAL_NIM_CACHE:/opt/nim/.cache" \
  -p 127.0.0.1:8000:8000 \
  nvcr.io/nim/arc/evo2:2

docker logs --tail 50 evo2-nim
curl --fail http://127.0.0.1:8000/v1/health/ready
```

Wait for readiness: first startup downloads weights. `NIM_VARIANT=7b` matters because the container defaults to 40B. The NGC key is for model/registry access; the raw local inference server does not require a bearer token.

In another terminal **on your laptop**, keep this SSH tunnel running:

```bash
ssh -N -L 8002:127.0.0.1:8000 YOUR_USER@YOUR_GPU_SERVER
```

Set the laptop's repository-root `.env` to:

```dotenv
EVO2_FORWARD_URL=
EVO2_BASE_URL=http://127.0.0.1:8002
EVO2_ACCESS_TOKEN=
```

Restart the backend, then run an Evo 2 investigation in the UI. The tunnel keeps the unauthenticated NIM endpoint private. Stop the GPU instance with your provider's controls when finished.

## What remains to validate

Helix compares reference/alternative sequence log-likelihood, averaged over both strands. This is a model-based sequence experiment, not a simulation of your cells or a disease probability. Hosted inference has been verified. Parity validation against the corresponding official scorer/checkpoint and scientific evaluation are still required before accuracy claims; self-hosted GPU execution remains untested.

Sources checked October 31, 2026: [hosted forward API](https://docs.api.nvidia.com/nim/reference/arc-evo2-7b-infer), [NIM support matrix](https://docs.nvidia.com/nim/bionemo/evo2/2.2.0/prerequisites), [NIM quickstart](https://docs.nvidia.com/nim/bionemo/evo2/2.2.0/quickstart-guide).
