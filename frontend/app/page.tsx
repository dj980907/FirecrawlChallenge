import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";

export default function HomePage() {
  return (
    <Box
      component="main"
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
      }}
    >
      <Container maxWidth="md">
        <Box sx={{ py: 8 }}>
          <Typography
            variant="overline"
            color="text.secondary"
            display="block"
            gutterBottom
          >
            Firecrawl Challenge
          </Typography>
          <Typography variant="h3" component="h1" gutterBottom fontWeight={600}>
            Next.js + FastAPI starter
          </Typography>
        </Box>
      </Container>
    </Box>
  );
}
