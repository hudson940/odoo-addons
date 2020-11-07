

 var url=  'http://pda.nacex.com/nacex_ws/';
 var urlWS=  url+'ws?';
 var base64topdf=  url+   "base64topdf.jsp";
 var base64topng=  url+   "base64topng.jsp";

 var credencialesWS='&user=[Su usuario]&pass=[Su MD5(password)]';

 var txtEs={
           pen:  'Par&aacute;metros de entrada',
           des:  'Descripci&oacute;n',
           rors: 'Retorno ordenado de par&aacute;metros de salida o error, <a href="es.codigos.html#erroresWS">ver c&oacute;digos de error</a>',
           rorf: 'Retorno de fichero en el elemento XML o error, <a href="es.codigos.html#erroresWS">ver c&oacute;digos de error</a>',
           dre:  'Respuesta: Retorno ',
           pcv:  'Petici&oacute;n (clave=valor)',
           pcp:  'Petici&oacute;n (posici&oacute;n)',
           pt0:  'Petici&oacute;n',
           re0:  'Respuesta',
           pt2:  'Petici&oacute;n 2',
           re2:  'Respuesta 2',
           pt3:  'Petici&oacute;n 3',
           re3:  'Respuesta 3',
           cod:  'C&oacute;digo',
           det:  'Detalle',
           vmt:  'Valores que admite el m&eacute;todo',
           dad:  'Desglose del array data',
           mlo:  'M&aacute;x. Long.',
           cla:   'clave'
           };

var txtEn={
           pen:  'In parameters',
           des:  'Description',
           rors: 'Out parameters, ordered or error, <a href="en.codigos.html#erroresWS">see error codes</a>',
           rorf: 'Out file inside of XML or error, <a href="en.codigos.html#erroresWS">see error codes</a>',
           dre:  'Response: result ',
           pcv:  'Request (key=value)',
           pcp:  'Request (ordered parameters)',
           pt0:  'Request',
           re0:  'Response',
           pt2:  'Request 2',
           re2:  'Response 2',
           pt3:  'Request 3',
           re3:  'Response 3',
           cod:  'Code',
           det:  'Detail',
           vmt:  'Method values',
           dad:  'Array data details',
           mlo:  'Max. Long',
           cla:   'key'
           };

var url = window.location.pathname;
var txt= url.substring(url.lastIndexOf('/')+1).substring(0,3)=='en.'? txtEn :txtEs;

 var method={
		 titulo: "",
		 metodo: "",
		 pie: "",
		 entrada: [],
		 data: [],
		 salida: [],
		 gets: [],
		 GetResp: [],
		 soap: "",
		 soapResp: "",
		 soap2: "",
		 soapResp2: "",
     	 soap3: "",
		 soapResp3: "",
		 get tituloF (){ return	this.titulo;	 },
		 get metodoF(){	 return this.metodo;	 },
		 get pieF(){	 return	this.pie;		 },
		 get entradaF(){ return	this.entrada;	 },
		 get dataF(){	 return this.data;	 },
		 get salidaF(){	 return this.salida;	 },
		 get getsF(){	 return this.gets;		 },
		 get GetRespF(){ return	this.GetResp;	 },

		  /**INFO:
		   tres espacios los cambia por un salto de línea al pintar la tabla
		  */
		 get soapF(){	 return this.soap.replace(/\s\s\s/g,"\r\n")		 },
		 get soapRespF(){return this.soapResp.replace(/\s\s\s/g,"\r\n")},
     	 get soapF2(){	 return this.soap2.replace(/\s\s\s/g,"\r\n")		 },
		 get soapRespF2(){return this.soapResp2.replace(/\s\s\s/g,"\r\n")},
     	 get soapF3(){	 return this.soap3.replace(/\s\s\s/g,"\r\n")},
		 get soapRespF3(){return this.soapResp3.replace(/\s\s\s/g,"\r\n")}
 };

var tablaMetodo= function (method, tipoRetorno){

	str=' <h1>'+method.tituloF+'</h1>';
	str+='<table  class="TBL_entrada"><thead>';
	str+='<tr><td colspan="2" ><h3>'+method.metodoF+'</h3></td></tr>';
	str+='<tr><td colspan = "2"><h4>'+txt.pen+'</h4></td></tr>';
	str+='<tr><td>Campo</td><td>'+txt.des+'</td></tr>';
	str+='</thead><tfoot>';
	str+='<tr><td colspan="2" >'+method.pieF+'</td></tr>';
	str+='</tfoot>';
  if    (method.entradaF != null && method.entradaF.length >0){
  	str+='<tbody>';
  	$.each(method.entradaF, function( key, value ) {	str+='    <tr><td>'+value[0]+'</td><td>'+value[1]+'</td></tr>'; 	});
  	str+=' </tbody>';
	}
  str+='</table>';

  if    (method.salidaF != null && method.salidaF.length >0){
    	str+=' <table class="TBL_salida">';
    	str+=' <thead >';

      if (tipoRetorno== null)
    	    str+=' 	<tr><td colspan = "2"><h4>'+txt.rors+'</h4></td></tr>';
    	else if (tipoRetorno== 'fichero')
          str+=' 	<tr><td colspan = "2"><h4>'+txt.rorf+'</h4></td></tr>';

      str+='<tr><td>'+txt.dre+'</a></td></tr>';
    	str+='	 </thead>';
    	str+='	  <tbody>';
    	$.each(method.salidaF, function( key, value ) {		str+='    <tr><td>'+value+'</td></tr>'; 	});
    	str+='	  </tbody>';
    	str+=' </table>';
    	str+='	 <br>';
     }
     if    (method.getsF[0] != null && method.getsF[0].length >0){
      	str+='<h3>GET</h3>';
      	str+='<h5>'+txt.pcv+'</h5>';
      	str+='	 <pre><xmp>'+method.getsF[0]+'</xmp></pre>';
      	str+='<h5>'+txt.pcp+'</h5>';
      	str+='	 <pre><xmp>'+method.getsF[1]+'</xmp></pre>';
      	str+='<h5>'+txt.re0+'</h5>';
      	str+='	 <pre><xmp>'+method.GetRespF[0]+'</xmp></pre>';
      }
  if    (method.soapF[0] != null && method.soapF[0].length >0){
    	str+='<h3>SOAP</h3>';
    	str+='<h4>'+txt.pt0+'</h4>';
    	str+='<pre><xmp>'+method.soapF+'</xmp></pre>';

    	str+='<h4>Respuesta</h4>';
    	str+='<pre><xmp>'+method.soapRespF+'</xmp></pre>';

      if (method.soapF2!= null && method.soapF2.length>0 ){
        str+='<h4>'+txt.pt2+'</h4>';
      	str+='<pre><xmp>'+method.soapF2+'</xmp></pre>';

      	str+='<h4>'+txt.re2+'</h4>';
      	str+='<pre><xmp>'+method.soapRespF2+'</xmp></pre>';
      }
       if (method.soapF3!= null &&  method.soapF3.length>0){
        str+='<h4>'+txt.pt3+'</h4>';
      	str+='<pre><xmp>'+method.soapF3+'</xmp></pre>';

      	str+='<h4>'+txt.re3+'</h4>';
      	str+='<pre><xmp>'+method.soapRespF3+'</xmp></pre>';
      }
  }
	str+='<hr>';

	return str;
 };

 var codes={
		 titulo: "",
		 pie: "",
		 codigos: [],
		 get tituloF (){ return	this.titulo;	 },
		 get pieF(){	 return	this.pie;		 },
		 get codigosF(){ return	this.codigos;	 }
 };


 var tablaCodigos= function (codes){

		str=' <h1>'+codes.tituloF+'</h1>';
		str+='<table  class="TBL_entrada"><thead>';
		str+='<tr><td>'+txt.cod+'</td><td>'+txt.des+'</td><td>'+txt.det+'</td></tr>';
		str+='</thead><tfoot>';
		str+='<tr><td colspan="3">'+codes.pieF+'</td></tr>';
		str+='</tfoot>';
		str+='<tbody>';
		$.each(codes.codigosF, function( key, value ) {
			str+='    <tr><td>'+value[0]+'</td><td>'+value[1]+'</td><td>'+value[2]+'</td></tr>';
			});
		str+=' </tbody>';
		str+='</table>';
		str+='<hr>';
		return str;
	 };

var tablaMetodoData= function (method, tipoRetorno){

	str=' <h1>'+method.tituloF+'</h1>';
	str+='<table  class="TBL_entrada"><thead>';
	str+='<tr><td colspan="2" ><h3>'+method.metodoF+'</h3></td></tr>';
	str+='<tr><td colspan = "2"><h4>'+txt.pen+'</h4></td></tr>';
	str+='<tr><td>Campo</td><td>'+txt.des+'</td></tr>';
	str+='</thead><tfoot>';
	str+='<tr><td colspan="2" >'+method.pieF+'</td></tr>';
	str+='</tfoot>';
    if    (method.entradaF != null && method.entradaF.length >0){
  	str+='<tbody>';
  	$.each(method.entradaF, function( key, value ) {	str+='    <tr><td>'+value[0]+'</td><td>'+value[1]+'</td></tr>'; 	});
  	str+=' </tbody>';
    }
	str+='</table>';

  if    (method.dataF != null && method.dataF.length >0){
  	str+='<table  class="TBL_data"><thead>';
      if (tipoRetorno== 'params')
  	      str+='<tr><td colspan="3"><h4>'+txt.vmt+'</h4></td></tr>';
      else
          str+='<tr><td colspan="3"><h4>'+txt.dad+'</h4></td></tr>';
  	str+='<tr><td>'+txt.cla+'</td><td>'+txt.des+'</td><td>'+txt.mlo+'</td></tr>';
  	str+='</thead><tfoot>';
  	str+='<tr><td colspan="3" ></td></tr>';
  	str+='</tfoot>';
  	str+='<tbody>';
  	$.each(method.dataF, function( key, value ) {
      /*if (value[3]== null)
        value[3]= '';*/
      str+='    <tr class = "'+value[3]+'"><td>'+value[0]+'</td><td>'+value[1]+'</td><td>'+value[2]+'</td></tr>'; 	});
  	str+=' </tbody>';
  	str+='</table>';
  }
  if    (method.salidaF.length >0){
    	str+=' <table class="TBL_salida">';
    	str+=' <thead >';
      if (tipoRetorno== null ||tipoRetorno== 'params')
    	    str+=' 	<tr><td colspan = "2"><h4>'+txt.rors+'</h4></td></tr>';
    	else if (tipoRetorno== 'fichero')
          str+=' 	<tr><td colspan = "2"><h4>'+txt.rorf+'</h4></td></tr>';

    	str+='<tr><td>'+txt.des+'</td></tr>';
    	str+='	 </thead>';
    	str+='	  <tbody>';
    	$.each(method.salidaF, function( key, value ) {		str+='    <tr><td>'+value+'</td></tr>'; 	});
    	str+='	  </tbody>';
    	str+=' </table>';
    	str+='	 <br>';
   }
     if    (method.getsF[0] != null &&  method.getsF[0].length >0){
      	str+='<h3>GET</h3>';
      	str+='<h5>'+txt.pcv+'</h5>';
      	str+='	 <pre><xmp>'+method.getsF[0]+'</xmp></pre>';
      	str+='<h5>'+txt.pcp+'</h5>';
      	str+='	 <pre><xmp>'+method.getsF[1]+'</xmp></pre>';
      	str+='<h5>'+txt.re0+'</h5>';
      	str+='	 <pre><xmp>'+method.GetRespF[0]+'</xmp></pre>';
      }
     if    (method.soapF != null && method.soapF.length >0){
        	str+='<h3>SOAP</h3>';
        	str+='<h4>'+txt.pt0+'</h4>';
        	str+='<pre><xmp>'+method.soapF+'</xmp></pre>';

        	str+='<h4>'+txt.re0+'</h4>';
        	str+='<pre><xmp>'+method.soapRespF+'</xmp></pre>';

          if (method.soapF2!= null && method.soapF2.length>0){
            str+='<h4>'+txt.pt0+'</h4>';
          	str+='<pre><xmp>'+method.soapF2+'</xmp></pre>';

          	str+='<h4>'+txt.re2+'</h4>';
          	str+='<pre><xmp>'+method.soapRespF2+'</xmp></pre>';
          }
           if (method.soapF3!= null&& method.soapF3.length>0){
            str+='<h4>'+txt.pt3+'</h4>';
          	str+='<pre><xmp>'+method.soapF3+'</xmp></pre>';

          	str+='<h4>'+txt.re3+'</h4>';
          	str+='<pre><xmp>'+method.soapRespF3+'</xmp></pre>';
          }
      }
	str+='<hr>';

	return str;
 };