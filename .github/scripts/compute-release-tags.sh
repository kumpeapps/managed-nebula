#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${REGISTRY:-}" || -z "${IMAGE_NAME:-}" || -z "${TAG_NAME:-}" ]]; then
  echo "Missing required env vars: REGISTRY, IMAGE_NAME, TAG_NAME" >&2
  exit 1
fi

RAW_MAKE_LATEST="${MAKE_LATEST_INPUT:-}"
RAW_IS_PRERELEASE="${IS_PRERELEASE_INPUT:-}"

MAKE_LATEST_NORMALIZED="$(echo "${RAW_MAKE_LATEST}" | tr '[:upper:]' '[:lower:]')"
IS_PRERELEASE_NORMALIZED="$(echo "${RAW_IS_PRERELEASE}" | tr '[:upper:]' '[:lower:]')"

case "${MAKE_LATEST_NORMALIZED}" in
  true|false|legacy)
    ;;
  *)
    MAKE_LATEST_NORMALIZED="legacy"
    ;;
esac

case "${IS_PRERELEASE_NORMALIZED}" in
  true|false)
    ;;
  *)
    IS_PRERELEASE_NORMALIZED="false"
    ;;
esac

TAGS="${REGISTRY}/${IMAGE_NAME}:${TAG_NAME}"

if [[ "${IS_PRERELEASE_NORMALIZED}" == "true" ]]; then
  echo "::notice::Pre-release detected - adding :latest-rc tag"
  TAGS="${TAGS},${REGISTRY}/${IMAGE_NAME}:latest-rc"
else
  case "${MAKE_LATEST_NORMALIZED}" in
    true)
      echo "::notice::Release marked as latest - adding :latest tag"
      TAGS="${TAGS},${REGISTRY}/${IMAGE_NAME}:latest"
      ;;
    false)
      echo "::notice::Release configured with make_latest=false - skipping :latest tag"
      ;;
    legacy)
      echo "::notice::Release uses make_latest=legacy - not forcing :latest tag"
      ;;
  esac
fi

if [[ -z "${GITHUB_OUTPUT:-}" ]]; then
  echo "GITHUB_OUTPUT is not set" >&2
  exit 1
fi

echo "tags=${TAGS}" >> "${GITHUB_OUTPUT}"
echo "normalized_make_latest=${MAKE_LATEST_NORMALIZED}" >> "${GITHUB_OUTPUT}"
echo "normalized_is_prerelease=${IS_PRERELEASE_NORMALIZED}" >> "${GITHUB_OUTPUT}"
