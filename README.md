# ShashGuru

A chess analyzer that takes a FEN or PGN and asks an LLM to analyse it.



##### Platforms

It should work with Unix and Windows.

Please open an issue if it doesn't. 

### Usage
Build and run from docker-compose-vllm.yml
I provide a shell script on linux for starting it: "refreshDockers.sh"



### Dependencies

ShashGuru integrates with external chess engines and tools:

[Alexander](https://github.com/amchess/Alexander) – licensed under the GNU General Public License v3 (GPLv3).

[ShashChess](https://github.com/amchess/ShashChess) – licensed under the GNU General Public License v3 (GPLv3).

These projects are bundled or invoked by ShashGuru under the terms of the GPLv3. Their source code is available at the links above.
