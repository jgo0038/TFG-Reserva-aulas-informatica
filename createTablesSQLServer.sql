
CREATE TABLE tipos (
	id_tipo VARCHAR(10) NOT NULL,
    descripcion VARCHAR(45),
    
    PRIMARY KEY (id_tipo),
    CONSTRAINT nombre_tipos CHECK (id_tipo='ORD' OR id_tipo='LAB' OR id_tipo='INF') 
);

CREATE TABLE edificios (
	id_edificio VARCHAR(10) NOT NULL,
    nombre VARCHAR(45),
    
    PRIMARY KEY (id_edificio)
);

CREATE TABLE propietarios (
	id_propietario VARCHAR(10) NOT NULL,
    descripcion VARCHAR(45),
    responsable VARCHAR(45),
    email VARCHAR(45),
    
    PRIMARY KEY (id_propietario)
);

CREATE TABLE aulas (
  nombre VARCHAR(45) NOT NULL,
  edificio VARCHAR(10) NOT NULL,
  tipo VARCHAR(10) NOT NULL,
  capacidad INT NOT NULL,
  propietario VARCHAR(10) NOT NULL,
  
  PRIMARY KEY (nombre),
  CONSTRAINT fk_tipo_aula FOREIGN KEY (tipo) REFERENCES tipos(id_tipo) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_edificio_aula FOREIGN KEY (edificio) REFERENCES edificios(id_edificio) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_propietario_aula FOREIGN KEY (propietario) REFERENCES propietarios(id_propietario) ON UPDATE CASCADE ON DELETE CASCADE);
  
  
 CREATE TABLE eventos (
	id int IDENTITY(1,1),
	aula VARCHAR(45) NOT NULL,
	evento VARCHAR(45) NOT NULL,
	email VARCHAR(45) NOT NULL,
	inicio datetime NOT NULL,
	fin datetime NOT NULL,
	creacion datetime NOT NULL,
	profesor VARCHAR(45) NOT NULL,
	
	CONSTRAINT fk_evento_aula FOREIGN KEY (aula) REFERENCES aulas(nombre) ON UPDATE CASCADE ON DELETE CASCADE
 );

 CREATE TABLE responsables (
	nombre VARCHAR(45) NOT NULL,
	id_propietario VARCHAR(10) NOT NULL,
	PRIMARY KEY (nombre, id_propietario),
	CONSTRAINT fk_responsables_aula FOREIGN KEY (nombre) REFERENCES aulas(nombre) ON UPDATE CASCADE ON DELETE CASCADE,
	CONSTRAINT fk_responsables_propietario FOREIGN KEY (id_propietario) REFERENCES propietarios(id_propietario) ON UPDATE CASCADE ON DELETE CASCADE
 );

  CREATE TABLE auditoria (
    id_auditoria int IDENTITY(1,1),
	id_evento INT NOT NULL,
    usuario VARCHAR(45) NOT NULL,
    fecha_modif datetime NOT NULL,
    identificador VARCHAR(20) NOT NULL,
    
    PRIMARY KEY (id_auditoria),
    CONSTRAINT identificador_auditoria CHECK (identificador='ALTA' OR identificador='BAJA' OR identificador='MODIF' ));

 CREATE TABLE [dbo].[user] (
	id int IDENTITY(1,1),
	access_token varchar(500) not null,
	refresh_token varchar(500) not null,
	email varchar(500),
	expires_on datetime,
	
	PRIMARY KEY (id));