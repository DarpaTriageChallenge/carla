// Copyright (c) 2024 Computer Vision Center (CVC) at the Universitat Autonoma
// de Barcelona (UAB).
//
// This work is licensed under the terms of the MIT license.
// For a copy, see <https://opensource.org/licenses/MIT>.

#include <PythonAPI.h>

void translator(const rpc::rpc_error &e) {
  std::stringstream ss;
  ss << e.what() << " in function " << e.get_function_name();
  /// @todo Supposedly we can extract the error string here as provided by the
  /// server with e.get_error().as<std::string>(), but it gives the wrong
  /// string.
  PyErr_SetString(PyExc_RuntimeError, ss.str().c_str());
}

void export_exception() {
  using namespace boost::python;
  register_exception_translator<rpc::rpc_error>(translator);
}
