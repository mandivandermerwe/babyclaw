# [1.1.0](https://github.com/sdkks/babyclaw/compare/v1.0.1...v1.1.0) (2026-05-11)


### Bug Fixes

* **claw:** copy proxy CA to tmpfs to avoid volume permission issues ([b353322](https://github.com/sdkks/babyclaw/commit/b353322b3742fb7ab45ed112d6b48246df005ea7))
* **claw:** defer NODE_EXTRA_CA_CERTS to entrypoint with retry poll ([4bfd67f](https://github.com/sdkks/babyclaw/commit/4bfd67febd1b3abc093ded0e7537d2431d60eedd))
* **compose:** correct Python tuple syntax in proxy healthcheck ([1eac815](https://github.com/sdkks/babyclaw/commit/1eac815e756a31b41af0b3b7018ed0771fbccb61))
* **compose:** proxy healthcheck checks listening port ([c6069d3](https://github.com/sdkks/babyclaw/commit/c6069d385c5e35d0e4efcfa6d878f93d09d77400))
* **compose:** squid healthcheck checks port instead of PID file ([68c8f8c](https://github.com/sdkks/babyclaw/commit/68c8f8c60abb3d9940a8a891e01a72570d401b5e))
* **compose:** wait for proxy and squid to be healthy before starting claw ([d629342](https://github.com/sdkks/babyclaw/commit/d62934273da949d9d017c317e037b5d176202d42))
* generate CA in /tmp then copy to persistent volume ([ae01957](https://github.com/sdkks/babyclaw/commit/ae019576a89590e346c89d0d406f65e5536584d2))
* generate mitmproxy CA with openssl in entrypoint ([fb5ee33](https://github.com/sdkks/babyclaw/commit/fb5ee33113f0b5cd0dd46490c2e6a2b6de69523a))
* **proxy:** chown /ca-share to mitmproxy so CA cert can be copied ([314225e](https://github.com/sdkks/babyclaw/commit/314225ebcd7ede7c90e3c73a30132d204851fef4))
* **proxy:** combine key+cert into mitmproxy-ca.pem ([045811a](https://github.com/sdkks/babyclaw/commit/045811a9dc91a2337986e19dcc32cc24e1e225e4))
* **proxy:** mitmproxy confdir crash and CA cert permissions ([fa500d5](https://github.com/sdkks/babyclaw/commit/fa500d58eee8fb4c819d8effcf3e58239ba899f2))
* run proxy entrypoint as root for tmpfs write access ([269a03c](https://github.com/sdkks/babyclaw/commit/269a03c81e2b6c6a0c7477608bdaacc736b690a3))
* use apt-get instead of apk in mitmproxy Dockerfile ([7d0520d](https://github.com/sdkks/babyclaw/commit/7d0520d9ec3a9eec852e0094103ced1271fee8e9))
* use Docker named volume for CA cert sharing ([4a4fc9a](https://github.com/sdkks/babyclaw/commit/4a4fc9a0912ff90bf328ab2814a4725533257c92))
* use mitmdump (headless) instead of mitmproxy (TUI) ([aabf113](https://github.com/sdkks/babyclaw/commit/aabf1133a9a3f81d9199a8195c87fb7d0a115e38))
* use mitmproxy built-in CA instead of hand-rolled certs ([073dcc5](https://github.com/sdkks/babyclaw/commit/073dcc5442d52939e5e9e029eae37fd81bd6c687))


### Features

* add domain bypass list to mitmproxy addon, route Telegram through proxy ([4ab407b](https://github.com/sdkks/babyclaw/commit/4ab407b7c24b14229c8ca5b6d05a2a96e1c2816e))

## [1.0.1](https://github.com/sdkks/babyclaw/compare/v1.0.0...v1.0.1) (2026-05-11)


### Bug Fixes

* config example ([304eabb](https://github.com/sdkks/babyclaw/commit/304eabbd85216b9d98229b30ea3ab13ad96d567c))

# 1.0.0 (2026-05-10)


### Bug Fixes

* add package-lock.json for CI npm ci ([757edcd](https://github.com/sdkks/babyclaw/commit/757edcd288413d75b2469b8ed530c766670cf596))


### Features

* add pre-commit hooks, commitlint, and semantic-release ([6292ff4](https://github.com/sdkks/babyclaw/commit/6292ff412bbd904ee0040d555b03d7a16308a20d))
