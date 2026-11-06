# Design and implementation differences

## research_notes.md

The historical intake has been explicitly marked superseded and linked to the current implementation contract and research report. It no longer claims training is pending. Its candidate-model ideas are not promises of completed experiments beyond the measured card track.

## architecture.md

- Live browser and network end-to-end verification could not be completed: the sandbox blocks outgoing loopback sockets and the browser preview timed out. In-memory HTTP parser/handler tests and JavaScript view checks cover logic, not rendered layout or live downloads.
- Static dashboard publication was attempted but source synchronization did not complete in the runtime. The site ID is retained in `dashboard-site/.openai/hosting.json` for a later retry. No deployed URL is claimed.

## README.md and component contracts

No additional implementation drift identified in the reviewed card-track contracts. Online payments and current-bank production validation remain unmeasured. A separate synthetic BAF account-opening stress test and age audit are now implemented; bank label-availability/behavior validation and local research review history are also implemented. These do not establish current-bank performance or demographic fairness on ULB.
