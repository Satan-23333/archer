# ArchER
ArchER (Architecture Error Resolver) is designed as a SoC-level verification framework targeting integration correctness in SoC designs.
## Directory Overview
- ```ErrorSet```: The dataset we use, which contains error codes.
- ```framework```: Contains the main program `archermain.py`, along with other necessary script files and configuration files.

## How to Use
- Install dependencies:
```bash
  pip install openai
```
- Set environment variables ```OPENAI_API_KEY``` to your own OpenAI API key.
- Check your simulation environment, modify the ```Makefile```.
- Run ```framework/archermain.py```. The script will automatically generate an output folder, save logs, and count the output results.
