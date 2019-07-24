# required to specify the c++ standard
cmake_minimum_required(VERSION 3.0)

# define project information
project(GooseBib)

# initialize list with binaries
set(PROJECT_BINARIES
  "bin/GbibClean"
  "bin/GbibList"
  "bin/GbibParse"
  "bin/GbibSelect"
  "bin/GbibCheckLink"
  "bin/GbibCheckAuthors")

# install binaries
INSTALL(PROGRAMS ${CMAKE_CURRENT_SOURCE_DIR}/${PROJECT_BINARIES} DESTINATION bin)

# print information to screen
message(STATUS "")
message(STATUS "+-------------------------------------------------------------------------------")
message(STATUS "|")
message(STATUS "| Use 'make install' to install the following scripts:")
message(STATUS "|")
message(STATUS "|   ${PROJECT_BINARIES}")
message(STATUS "|")
message(STATUS "| in:")
message(STATUS "|")
message(STATUS "|   ${CMAKE_INSTALL_PREFIX}")
message(STATUS "|")
message(STATUS "| To specify a custom directory (e.g. '~/opt'), add the following cmake-option:")
message(STATUS "|")
message(STATUS "|   cmake ... -DCMAKE_INSTALL_PREFIX='~/opt'")
message(STATUS "|")
message(STATUS "| You may want to add the following line to your '~/.bashrc' (or equivalent):")
message(STATUS "|")
message(STATUS "|   export PATH=${CMAKE_INSTALL_PREFIX}/bin:$PATH")
message(STATUS "|")
message(STATUS "+-------------------------------------------------------------------------------")
message(STATUS "")
