package planilla.mini;

import java.math.BigDecimal;
import java.util.logging.Logger;

public class Boleta {

  private static final Logger LOG = Logger.getLogger(Boleta.class.getName());

  private BigDecimal montoNeto;

  public void emitir(BigDecimal neto) {
    this.montoNeto = neto;
    LOG.info("boleta emitida");
  }
}
