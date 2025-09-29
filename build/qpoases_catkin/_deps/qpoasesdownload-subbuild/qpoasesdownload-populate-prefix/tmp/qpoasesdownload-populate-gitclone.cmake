
if(NOT "/home/ludan/old_ws/build/qpoases_catkin/_deps/qpoasesdownload-subbuild/qpoasesdownload-populate-prefix/src/qpoasesdownload-populate-stamp/qpoasesdownload-populate-gitinfo.txt" IS_NEWER_THAN "/home/ludan/old_ws/build/qpoases_catkin/_deps/qpoasesdownload-subbuild/qpoasesdownload-populate-prefix/src/qpoasesdownload-populate-stamp/qpoasesdownload-populate-gitclone-lastrun.txt")
  message(STATUS "Avoiding repeated git clone, stamp file is up to date: '/home/ludan/old_ws/build/qpoases_catkin/_deps/qpoasesdownload-subbuild/qpoasesdownload-populate-prefix/src/qpoasesdownload-populate-stamp/qpoasesdownload-populate-gitclone-lastrun.txt'")
  return()
endif()

execute_process(
  COMMAND ${CMAKE_COMMAND} -E remove_directory "/home/ludan/old_ws/build/qpoases_catkin/download"
  RESULT_VARIABLE error_code
  )
if(error_code)
  message(FATAL_ERROR "Failed to remove directory: '/home/ludan/old_ws/build/qpoases_catkin/download'")
endif()

# try the clone 3 times in case there is an odd git clone issue
set(error_code 1)
set(number_of_tries 0)
while(error_code AND number_of_tries LESS 3)
  execute_process(
    COMMAND "/usr/bin/git"  clone --no-checkout "https://github.com/coin-or/qpOASES" "download"
    WORKING_DIRECTORY "/home/ludan/old_ws/build/qpoases_catkin"
    RESULT_VARIABLE error_code
    )
  math(EXPR number_of_tries "${number_of_tries} + 1")
endwhile()
if(number_of_tries GREATER 1)
  message(STATUS "Had to git clone more than once:
          ${number_of_tries} times.")
endif()
if(error_code)
  message(FATAL_ERROR "Failed to clone repository: 'https://github.com/coin-or/qpOASES'")
endif()

execute_process(
  COMMAND "/usr/bin/git"  checkout 268b2f2659604df27c82aa6e32aeddb8c1d5cc7f --
  WORKING_DIRECTORY "/home/ludan/old_ws/build/qpoases_catkin/download"
  RESULT_VARIABLE error_code
  )
if(error_code)
  message(FATAL_ERROR "Failed to checkout tag: '268b2f2659604df27c82aa6e32aeddb8c1d5cc7f'")
endif()

set(init_submodules TRUE)
if(init_submodules)
  execute_process(
    COMMAND "/usr/bin/git"  submodule update --recursive --init 
    WORKING_DIRECTORY "/home/ludan/old_ws/build/qpoases_catkin/download"
    RESULT_VARIABLE error_code
    )
endif()
if(error_code)
  message(FATAL_ERROR "Failed to update submodules in: '/home/ludan/old_ws/build/qpoases_catkin/download'")
endif()

# Complete success, update the script-last-run stamp file:
#
execute_process(
  COMMAND ${CMAKE_COMMAND} -E copy
    "/home/ludan/old_ws/build/qpoases_catkin/_deps/qpoasesdownload-subbuild/qpoasesdownload-populate-prefix/src/qpoasesdownload-populate-stamp/qpoasesdownload-populate-gitinfo.txt"
    "/home/ludan/old_ws/build/qpoases_catkin/_deps/qpoasesdownload-subbuild/qpoasesdownload-populate-prefix/src/qpoasesdownload-populate-stamp/qpoasesdownload-populate-gitclone-lastrun.txt"
  RESULT_VARIABLE error_code
  )
if(error_code)
  message(FATAL_ERROR "Failed to copy script-last-run stamp file: '/home/ludan/old_ws/build/qpoases_catkin/_deps/qpoasesdownload-subbuild/qpoasesdownload-populate-prefix/src/qpoasesdownload-populate-stamp/qpoasesdownload-populate-gitclone-lastrun.txt'")
endif()

