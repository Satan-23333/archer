include ./run.mk

.DEFAULT_GOAL := all

all:
	@make -f run.mk runcase CASE=hello_world SIM=vcs COV=false CLEAN=true DUMP=on

ver:
	@make -f run.mk runcase CASE=hello_world SIM=verilator COV=false CLEAN=true DUMP=on
xml:
	@make -f run.mk compile CASE=hello_world SIM=verilator COV=false CLEAN=true XML=true
	@echo "Generate XML done!"
py:
	python ./extractor.py ./work/obj_dir/Vtop.xml
