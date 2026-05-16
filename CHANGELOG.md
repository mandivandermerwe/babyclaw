# [1.2.0](https://github.com/sdkks/babyclaw/compare/v1.1.5...v1.2.0) (2026-05-16)


### Features

* change search engine to duckduckgo ([05876bc](https://github.com/sdkks/babyclaw/commit/05876bc7354c4eeebb8d0a673fda6c6c456cc46e))

## [1.1.5](https://github.com/sdkks/babyclaw/compare/v1.1.4...v1.1.5) (2026-05-15)


### Bug Fixes

* **proxy:** rewrite channel type to "group" instead of "supergroup" ([51e6580](https://github.com/sdkks/babyclaw/commit/51e65800a7d980f6b3a659f718eaf421ebd1b936))

## [1.1.4](https://github.com/sdkks/babyclaw/compare/v1.1.3...v1.1.4) (2026-05-12)


### Bug Fixes

* **proxy:** handle channel_post and edited_channel_post as message-like updates ([acf3d79](https://github.com/sdkks/babyclaw/commit/acf3d7946bea980220d5c68bb2a893c5f441d1be))
* **proxy:** remove hard is_bot check, cache is source of truth for reply enrichment ([567af06](https://github.com/sdkks/babyclaw/commit/567af06f32130a2e52a1162e17d0e08916fc710c))
* **proxy:** rewrite channel_post → message with synthetic sender for OpenClaw compatibility ([5eb8260](https://github.com/sdkks/babyclaw/commit/5eb826057847ebae53da8bb26215450168b48ce6))
* **proxy:** rewrite chat.type channel → supergroup for OpenClaw routing ([3ff0e52](https://github.com/sdkks/babyclaw/commit/3ff0e5250ef1e6e85a5f06ceae53a2afcaf7e4ee))
* **proxy:** skip bot-sent messages to prevent feedback loops in channels ([3497bc3](https://github.com/sdkks/babyclaw/commit/3497bc353a8631e7045e2f90ad0d2eaa185909ed))

## [1.1.3](https://github.com/sdkks/babyclaw/compare/v1.1.2...v1.1.3) (2026-05-12)


### Bug Fixes

* **examples:** sync public templates with private canonical config ([f58d885](https://github.com/sdkks/babyclaw/commit/f58d8851c3baac6c65a4c1734bee57a463df590a))
* **proxy:** create proxy-state dir with mitmproxy ownership for reply cache ([92ccc27](https://github.com/sdkks/babyclaw/commit/92ccc2793c455ff5f8a84b446d39617946318b7a))

## [1.1.2](https://github.com/sdkks/babyclaw/compare/v1.1.1...v1.1.2) (2026-05-11)


### Bug Fixes

* **claw:** detect and regenerate stale agent model on boot ([05d4591](https://github.com/sdkks/babyclaw/commit/05d4591dbf2ed70b79d785dd2028794d9fb7d84e))

## [1.1.1](https://github.com/sdkks/babyclaw/compare/v1.1.0...v1.1.1) (2026-05-11)


### Bug Fixes

* **proxy:** tunnel Telegram without TLS interception ([a310dc1](https://github.com/sdkks/babyclaw/commit/a310dc156770f35e8b88f3bddb4a7abb3d4c1c41))

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
