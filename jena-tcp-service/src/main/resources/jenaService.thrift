/*
	Compile with:
thrift -r --gen py jenaService.thrift

*/

# Thrift Tutorial
# Mark Slee (mcslee@facebook.com)
#
# This file aims to teach you how to use Thrift, in a .thrift file. Neato. The
# first thing to notice is that .thrift files support standard shell comments.
# This lets you make your thrift file executable and include your Thrift build
# step on the top line. And you can place comments like this anywhere you like.
#
# Before running this file, you will need to have installed the thrift compiler
# into /usr/local/bin.

/** Types
 * The first thing to know about are types. The available types in Thrift are:
 *
 *  bool        Boolean, one byte
 *  i8 (byte)   Signed 8-bit integer
 *  i16         Signed 16-bit integer
 *  i32         Signed 32-bit integer
 *  i64         Signed 64-bit integer
 *  double      64-bit floating point value
 *  string      String
 *  binary      Blob (byte array)
 *  map<t1,t2>  Map from one type to another
 *  list<t1>    Ordered list of one type
 *  set<t1>     Set of unique elements of one type
 *
 */
// It supports simple C comments too.


/**
 * Thrift files can reference other Thrift files to include common struct
 * and service definitions. These are found using the current path, or by
 * searching relative to any paths specified with the -I compiler flag.
 *
 * Included objects are accessed using the name of the .thrift file as a
 * prefix. i.e. BinaryRDF.SharedObject
 */
#include "BinaryRDF.thrift"

/**
 * Thrift files can namespace, package, or prefix their output in various
 * target languages.
 */

namespace java   jenaService
namespace python jenaService



/**
 * Structs are the basic complex data structures. They are comprised of fields
 * which each have an integer identifier, a type, a symbolic name, and an
 * optional default value.
 *
 * Fields can be declared "optional", which ensures they will not be included
 * in the serialized output if they aren't set.  Note that this requires some
 * manual management in some languages.
 */
#struct Work {
#  1: i32 num1 = 0,
#  2: i32 num2,
#  3: Operation op,
#  4: optional string comment,
#}

/**
 * Structs can also be exceptions, if they are nasty.
 */
#exception InvalidOperation {
#  1: i32 whatOp,
#  2: string why
#}

#struct RDF_Graph {
#1: list<BinaryRDF.RDF_StreamRow> graph
#}



/**
 * A service to invoke Jena Reasoner and answer the complemented RDF graph.
 */
service JenaReasoner {

  /**
   * A method to ensure quickly that server side is running.
   */
   bool ping(),


  /**
   * Just testing RDF transportation: save RDF graph as a file.
   */
   void saveRdf(1:binary rdfData, 2:string filename),


  /**
   * Do the reasoning and return the complemented RDF graph.
   */
   binary runReasoner(1:binary rdfData, 2:string rulePaths) /* throws (1:InvalidOperation ouch) */ ,

   /**
    * Stop the server.
    */
   oneway void stop()

}

/**
 * That just about covers the basics. Take a look in the test/ folder for more
 * detailed examples. After you run this file, your generated code shows up
 * in folders with names gen-<language>. The generated code isn't too scary
 * to look at. It even has pretty indentation.
 */
