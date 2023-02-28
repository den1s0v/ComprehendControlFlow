
# build a JAR
mvn package assembly:single

# copy result jar to python lib jena/ dir where it can be run from
cp -f target/Jena-1.0-SNAPSHOT-jar-with-dependencies.jar ../python-lib/jena/Jena.jar

